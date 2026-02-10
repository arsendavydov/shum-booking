from fastapi import APIRouter, Body, HTTPException, Request, Response

from src.api.dependencies import AuthServiceDep, CurrentUserDep, DBDep, UsersServiceDep
from src.config import settings
from src.metrics.collectors import (
    auth_failed_attempts_total,
    auth_logins_total,
    auth_refresh_tokens_total,
    auth_registrations_total,
)
from src.metrics.helpers import should_collect_metrics
from src.middleware.rate_limiting import rate_limit
from src.schemas.common import MessageResponse
from src.schemas.users import (
    RefreshTokenRequest,
    SchemaUser,
    TokenResponse,
    UserRequestLogin,
    UserRequestRegister,
    UserResponse,
)
from src.utils.db_manager import DBManager

router = APIRouter()


@router.post(
    "/register",
    summary="Регистрация нового пользователя",
    description="Регистрирует нового пользователя. Email и пароль обязательны. Остальные поля опциональны. Пароль хешируется перед сохранением.",
    response_model=UserResponse,
    status_code=201,
)
@rate_limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def register_user(
    request: Request,  # noqa: ARG001
    auth_service: AuthServiceDep,
    users_service: UsersServiceDep,
    user_data: UserRequestRegister = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Минимальная регистрация",
                "description": "Регистрация только с email и паролем",
                "value": {"email": "user@example.com", "password": "securepass123"},
            },
            "2": {
                "summary": "Полная регистрация",
                "description": "Регистрация со всеми полями",
                "value": {
                    "email": "user@example.com",
                    "password": "securepass123",
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "telegram_id": "123456789",
                    "pachca_id": "pachca_123",
                },
            },
        },
    ),
) -> UserResponse:
    """
    Зарегистрировать нового пользователя.

    Обязательные поля:
    - email: Email пользователя (должен быть уникальным)
    - password: Пароль (минимум 8 символов, будет захеширован)

    Опциональные поля:
    - first_name: Имя пользователя
    - last_name: Фамилия пользователя
    - telegram_id: Telegram ID пользователя
    - pachca_id: Pachca ID пользователя

    Args:
        auth_service: Сервис для работы с аутентификацией
        users_service: Сервис для работы с пользователями
        user_data: Данные для регистрации

    Returns:
        Созданный пользователь с ID

    Raises:
        HTTPException: 409 если email уже существует
        HTTPException: 422 если данные невалидны (автоматически через Pydantic)
    """
    async with DBManager.transaction(users_service.session):
        # Подготовка данных пользователя (хеширование пароля)
        user_register_data = auth_service.prepare_user_data_for_registration(user_data)

        # Создание пользователя через сервис
        user = await users_service.register_user(user_register_data)

    # Метрика регистрации
    if should_collect_metrics():
        auth_registrations_total.inc()

    # Преобразуем SchemaUser в UserResponse (они идентичны, но для ясности используем UserResponse) 
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    summary="Вход пользователя",
    description="Аутентифицирует пользователя по email и паролю. Возвращает JWT токен в JSON ответе и устанавливает его в HTTP-only cookie.",
    response_model=TokenResponse,
)
@rate_limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def login_user(
    request: Request,  # noqa: ARG001 1
    response: Response,
    db: DBDep,
    auth_service: AuthServiceDep,
    login_data: UserRequestLogin = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Вход пользователя",
                "description": "Вход с email и паролем",
                "value": {"email": "user@example.com", "password": "securepass123"},
            }
        },
    ),
) -> TokenResponse:
    """
    Войти в систему.

    Проверяет email и пароль пользователя. При успешной аутентификации
    возвращает JWT токен для доступа к защищенным эндпоинтам.

    Args:
        db: Сессия базы данных
        login_data: Данные для входа (email и password)

    Returns:
        TokenResponse с JWT токеном и типом токена

    Raises:
        HTTPException: 401 если email или пароль неверны
        HTTPException: 422 если данные невалидны (автоматически через Pydantic)
    """
    repo = DBManager.get_users_repository(db)
    # Поиск пользователя по email (получаем ORM объект для доступа к hashed_password)
    user_orm = await repo.get_orm_by_email(login_data.email)

    if user_orm is None:
        if should_collect_metrics():
            auth_logins_total.labels(status="failure").inc()
            auth_failed_attempts_total.labels(reason="user_not_found").inc()
        raise HTTPException(status_code=401, detail="Пользователь с таким email не найден")

    # Проверка пароля
    if not user_orm.hashed_password or not auth_service.verify_password(login_data.password, user_orm.hashed_password):
        if should_collect_metrics():
            auth_logins_total.labels(status="failure").inc()
            auth_failed_attempts_total.labels(reason="invalid_password").inc()
        raise HTTPException(status_code=401, detail="Неверный пароль")

    # Создание JWT токена
    access_token = auth_service.create_access_token(data={"sub": str(user_orm.id), "email": user_orm.email})

    # Создание и сохранение refresh токена
    refresh_token_repo = DBManager.get_refresh_tokens_repository(db)
    refresh_token = auth_service.generate_refresh_token()
    expires_at = auth_service.get_refresh_token_expires_at()

    async with DBManager.transaction(db):
        await refresh_token_repo.create_token(user_orm.id, refresh_token, expires_at)

    # Установка токена в HTTP-only cookie
    expire_minutes = auth_service.expire_minutes
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=expire_minutes * 60,  # Время жизни в секундах
        httponly=True,  # Защита от XSS атак (JavaScript не может получить доступ)
        secure=auth_service.cookie_secure,  # Только через HTTPS (настраивается через переменную окружения)
        samesite="lax",  # Защита от CSRF атак
        path="/",  # Доступен для всех путей
    )

    # Метрика успешного входа
    if should_collect_metrics():
        auth_logins_total.labels(status="success").inc()

    # Возвращаем токены в JSON ответе
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.get(
    "/me",
    summary="Получить данные текущего пользователя",
    description="Возвращает данные текущего авторизованного пользователя на основе JWT токена. Токен может быть передан в cookie (access_token) или в заголовке Authorization (Bearer token).",
    response_model=SchemaUser,
)
async def get_current_user_info(current_user: CurrentUserDep) -> SchemaUser:
    """
    Получить данные текущего авторизованного пользователя.

    Проверяет JWT токен и возвращает данные пользователя, который отправил запрос.
    Токен может быть передан:
    - В HTTP-only cookie с именем "access_token"
    - В заголовке Authorization: "Bearer <token>"

    Args:
        current_user: Текущий авторизованный пользователь (получается из JWT токена)

    Returns:
        SchemaUser: Данные текущего пользователя

    Raises:
        HTTPException: 401 если токен невалиден, отсутствует или пользователь не найден
    """
    return current_user


@router.post(
    "/refresh",
    summary="Обновить access токен",
    description="Обновляет access токен используя refresh токен. Возвращает новый access токен и новый refresh токен.",
    response_model=TokenResponse,
)
@rate_limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def refresh_token(
    request: Request,  # noqa: ARG001
    response: Response,
    db: DBDep,
    auth_service: AuthServiceDep,
    refresh_data: RefreshTokenRequest = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Обновление токена",
                "description": "Обновление access токена с помощью refresh токена",
                "value": {"refresh_token": "refresh_token_string"},
            }
        },
    ),
) -> TokenResponse:
    """
    Обновить access токен.

    Проверяет refresh токен и выдает новый access токен и новый refresh токен.
    Старый refresh токен отзывается.

    Args:
        db: Сессия базы данных
        auth_service: Сервис для работы с аутентификацией
        refresh_data: Данные с refresh токеном

    Returns:
        TokenResponse с новым access токеном и новым refresh токеном

    Raises:
        HTTPException: 401 если refresh токен невалиден или истек
    """
    refresh_token_repo = DBManager.get_refresh_tokens_repository(db)

    # Проверяем refresh токен
    refresh_token_orm = await refresh_token_repo.get_by_token(refresh_data.refresh_token)

    if refresh_token_orm is None:
        if should_collect_metrics():
            auth_refresh_tokens_total.labels(status="failure").inc()
        raise HTTPException(status_code=401, detail="Невалидный или истекший refresh токен")

    # Получаем пользователя
    users_repo = DBManager.get_users_repository(db)
    user_orm = await users_repo.get_by_field_orm("id", refresh_token_orm.user_id)

    if user_orm is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    # Отзываем старый refresh токен
    async with DBManager.transaction(db):
        await refresh_token_repo.revoke_token(refresh_data.refresh_token)

        # Создаем новый access токен
        access_token = auth_service.create_access_token(data={"sub": str(user_orm.id), "email": user_orm.email})

        # Создаем новый refresh токен
        new_refresh_token = auth_service.generate_refresh_token()
        expires_at = auth_service.get_refresh_token_expires_at()
        await refresh_token_repo.create_token(user_orm.id, new_refresh_token, expires_at)

    # Установка нового access токена в HTTP-only cookie
    expire_minutes = auth_service.expire_minutes
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=expire_minutes * 60,
        httponly=True,
        secure=auth_service.cookie_secure,
        samesite="lax",
        path="/",
    )

    # Метрика успешного обновления токена
    if should_collect_metrics():
        auth_refresh_tokens_total.labels(status="success").inc()

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token, token_type="bearer")


@router.post(
    "/logout",
    summary="Выход пользователя",
    description="Выходит из системы, удаляя JWT токен из cookie и отзывая все refresh токены пользователя. Требуется аутентификация через JWT токен.",
    response_model=MessageResponse,
)
async def logout_user(
    response: Response,
    db: DBDep,
    current_user: CurrentUserDep,
) -> MessageResponse:
    """
    Выйти из системы.

    Удаляет JWT токен из HTTP-only cookie и отзывает все refresh токены пользователя.
    Требуется валидный JWT токен для подтверждения, что пользователь действительно авторизован.

    Args:
        response: FastAPI Response объект для установки cookie
        db: Сессия базы данных
        current_user: Текущий авторизованный пользователь (из JWT токена)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 401 если пользователь не аутентифицирован
    """
    # Отзываем все refresh токены пользователя
    refresh_token_repo = DBManager.get_refresh_tokens_repository(db)
    async with DBManager.transaction(db):
        await refresh_token_repo.revoke_all_user_tokens(current_user.id)

    # Удаляем токен из cookie
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite="lax",
    )

    return MessageResponse(status="OK")
