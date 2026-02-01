from fastapi import APIRouter, Body, HTTPException, Query

from src.api import DBDep, PaginationDep
from src.schemas import MessageResponse
from src.utils.api_helpers import get_or_404
from src.schemas.users import SchemaUser, UserPATCH, UserRegister
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
async def update_user(user_id: int, db: DBDep, user: UserRegister = Body(...)) -> MessageResponse:
    """
    Полное обновление пользователя.

    Args:
        user_id: ID пользователя для обновления
        db: Сессия базы данных
        user: Данные для обновления

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если пользователь с указанным ID не найден
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_users_repository(db)

        # Проверяем существование пользователя
        existing_user = await repo.get_by_id(user_id)
        if existing_user is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Проверяем уникальность email, если он изменяется
        user_data = user.model_dump(exclude_none=True)
        if "email" in user_data and user_data["email"] != existing_user.email:
            if await repo.exists_by_email(user_data["email"]):
                raise HTTPException(status_code=409, detail=f"Пользователь с email {user_data['email']} уже существует")

        try:
            updated_user = await repo.edit(id=user_id, **user_data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if updated_user is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

    return MessageResponse(status="OK")


@router.patch(
    "/{user_id}",
    summary="Частичное обновление пользователя",
    description="Частично обновляет информацию о пользователе по указанному ID",
    response_model=MessageResponse,
)
async def partial_update_user(user_id: int, db: DBDep, user: UserPATCH = Body(...)) -> MessageResponse:
    """
    Частичное обновление пользователя.

    Args:
        user_id: ID пользователя для обновления
        db: Сессия базы данных
        user: Данные для обновления (опционально)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если пользователь с указанным ID не найден
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_users_repository(db)
        existing_user = await repo.get_by_id(user_id)
        if existing_user is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Обновляем только переданные поля
        update_data = user.model_dump(exclude_unset=True)
        if update_data:
            await repo.update(id=user_id, **update_data)

    return MessageResponse(status="OK")


@router.delete(
    "/{user_id}",
    summary="Удалить пользователя",
    description="Удаляет пользователя по указанному ID",
    response_model=MessageResponse,
)
async def delete_user(user_id: int, db: DBDep) -> MessageResponse:
    """
    Удалить пользователя.

    Args:
        user_id: ID пользователя для удаления
        db: Сессия базы данных

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если пользователь с указанным ID не найден
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_users_repository(db)
        try:
            deleted = await repo.delete(user_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not deleted:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

    return MessageResponse(status="OK")
