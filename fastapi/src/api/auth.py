from fastapi import APIRouter, Body, HTTPException, Response

from src.api.dependencies import AuthServiceDep, CurrentUserDep, DBDep
from src.config import settings
from src.schemas.common import MessageResponse
from src.schemas.users import SchemaUser, TokenResponse, UserRequestLogin, UserRequestRegister, UserResponse
from src.utils.db_manager import DBManager

router = APIRouter()


@router.post(
    "/register",
    summary="Регистрация нового пользователя",
    description="Регистрирует нового пользователя. Email и пароль обязательны. Остальные поля опциональны. Пароль хешируется перед сохранением.",
    response_model=UserResponse,
    status_code=201,
)
async def register_user(
    db: DBDep,
    auth_service: AuthServiceDep,
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
        db: Сессия базы данных
        user_data: Данные для регистрации

    Returns:
        Созданный пользователь с ID

    Raises:
        HTTPException: 409 если email уже существует
        HTTPException: 422 если данные невалидны (автоматически через Pydantic)
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_users_repository(db)
        # Проверка уникальности email
        if await repo.exists_by_email(user_data.email):
            raise HTTPException(status_code=409, detail=f"Пользователь с email {user_data.email} уже существует")

        # Подготовка данных пользователя (хеширование пароля)
        user_register_data = auth_service.prepare_user_data_for_registration(user_data)

        # Создание пользователя через репозиторий
        user = await repo.create(**user_register_data.model_dump(exclude_none=True))

    # Преобразуем SchemaUser в UserResponse (они идентичны, но для ясности используем UserResponse)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    summary="Вход пользователя",
    description="Аутентифицирует пользователя по email и паролю. Возвращает JWT токен в JSON ответе и устанавливает его в HTTP-only cookie.",
    response_model=TokenResponse,
)
async def login_user(
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
        raise HTTPException(status_code=401, detail="Пользователь с таким email не найден")

    # Проверка пароля
    if not user_orm.hashed_password or not auth_service.verify_password(login_data.password, user_orm.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный пароль")

    # Создание JWT токена
    access_token = auth_service.create_access_token(data={"sub": str(user_orm.id), "email": user_orm.email})

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

    # Возвращаем токен также в JSON ответе
    return TokenResponse(access_token=access_token, token_type="bearer")


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
    "/logout",
    summary="Выход пользователя",
    description="Выходит из системы, удаляя JWT токен из cookie. Требуется аутентификация через JWT токен. Токен становится недействительным на клиенте, но остается валидным до истечения срока действия.",
    response_model=MessageResponse,
)
async def logout_user(response: Response, _current_user: CurrentUserDep) -> MessageResponse:
    """
    Выйти из системы.

    Удаляет JWT токен из HTTP-only cookie.
    Требуется валидный JWT токен для подтверждения, что пользователь действительно авторизован.

    Примечание: JWT токены являются stateless, поэтому сервер не может
    инвалидировать токен на сервере. Токен останется технически валидным
    до истечения срока действия, но клиент больше не будет его использовать.

    Args:
        response: FastAPI Response объект для установки cookie
        current_user: Текущий авторизованный пользователь (из JWT токена)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 401 если пользователь не аутентифицирован
    """
    # Удаляем токен из cookie
    # Используем те же параметры, что и при установке cookie
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,  # Используем то же значение, что и при установке
        samesite="lax",
    )

    return MessageResponse(status="OK")
