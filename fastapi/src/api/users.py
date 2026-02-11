from fastapi import APIRouter, Body, HTTPException, Query

from src.api.dependencies import DBDep, PaginationDep, UsersServiceDep
from src.schemas import MessageResponse
from src.schemas.users import SchemaUser, UserPATCH, UserRegister
from src.utils.api_helpers import get_or_404
from src.utils.db_manager import DBManager

router = APIRouter()


@router.get(
    "",
    summary="Получить список пользователей",
    description="Возвращает список всех пользователей с поддержкой пагинации. Поддерживает фильтрацию по email.",
    response_model=list[SchemaUser],
)
async def get_users(
    pagination: PaginationDep,
    db: DBDep,
    email: str | None = Query(default=None, description="Фильтр по email (точное совпадение)"),
) -> list[SchemaUser]:
    """
    Получить список пользователей с поддержкой пагинации и фильтрации.

    Args:
        pagination: Параметры пагинации (page и per_page)
        db: Сессия базы данных
        email: Опциональный фильтр по email (точное совпадение)

    Returns:
        Список пользователей с учетом пагинации и фильтров
    """
    repo = DBManager.get_users_repository(db)
    users = await repo.get_paginated(page=pagination.page, per_page=pagination.per_page, email=email)
    return users


@router.get(
    "/{user_id}",
    summary="Получить пользователя по ID",
    description="Возвращает информацию о пользователе по указанному ID",
    response_model=SchemaUser,
)
async def get_user_by_id(user_id: int, db: DBDep) -> SchemaUser:
    """
    Получить пользователя по ID.

    Args:
        user_id: ID пользователя
        db: Сессия базы данных

    Returns:
        Информация о пользователе

    Raises:
        HTTPException: 404 если пользователь с указанным ID не найден
    """
    repo = DBManager.get_users_repository(db)
    user = await get_or_404(repo.get_by_id, user_id, "Пользователь")
    return user


@router.put(
    "/{user_id}",
    summary="Полное обновление пользователя",
    description="Полностью обновляет информацию о пользователе по указанному ID",
    response_model=MessageResponse,
)
async def update_user(
    user_id: int,
    users_service: UsersServiceDep,
    user: UserRegister = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Полное обновление пользователя",
                "description": "Обновление всех полей пользователя",
                "value": {
                    "email": "ivan.petrov@async-black.ru",
                    "hashed_password": "$2b$12$...",
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "telegram_id": 123456789,
                    "pachca_id": 987654321,
                },
            }
        },
    ),
) -> MessageResponse:
    """
    Полное обновление пользователя.

    Args:
        user_id: ID пользователя для обновления
        user: Данные для обновления
        users_service: Сервис для работы с пользователями

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если пользователь с указанным ID не найден
    """
    async with DBManager.transaction(users_service.session):
        await users_service.update_user(user_id=user_id, user_data=user)

    return MessageResponse(status="OK")


@router.patch(
    "/{user_id}",
    summary="Частичное обновление пользователя",
    description="Частично обновляет информацию о пользователе по указанному ID",
    response_model=MessageResponse,
)
async def partial_update_user(
    user_id: int,
    users_service: UsersServiceDep,
    user: UserPATCH = Body(
        ...,
        openapi_examples={
            "1": {"summary": "Обновить только имя", "value": {"first_name": "Иван"}},
            "2": {"summary": "Обновить email", "value": {"email": "new.email@async-black.ru"}},
            "3": {
                "summary": "Обновить несколько полей",
                "value": {"first_name": "Мария", "last_name": "Иванова", "telegram_id": 987654321},
            },
        },
    ),
) -> MessageResponse:
    """
    Частичное обновление пользователя.

    Args:
        user_id: ID пользователя для обновления
        user: Данные для обновления (опционально)
        users_service: Сервис для работы с пользователями

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если пользователь с указанным ID не найден
    """
    async with DBManager.transaction(users_service.session):
        update_data = user.model_dump(exclude_unset=True)
        if update_data:
            await users_service.partial_update_user(user_id=user_id, user_data=update_data)

    return MessageResponse(status="OK")


@router.delete(
    "/{user_id}",
    summary="Удалить пользователя",
    description="Удаляет пользователя по указанному ID",
    response_model=MessageResponse,
)
async def delete_user(user_id: int, users_service: UsersServiceDep) -> MessageResponse:
    """
    Удалить пользователя.

    Args:
        user_id: ID пользователя для удаления
        users_service: Сервис для работы с пользователями

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если пользователь с указанным ID не найден
    """
    async with DBManager.transaction(users_service.session):
        deleted = await users_service.delete_user(user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

    return MessageResponse(status="OK")
