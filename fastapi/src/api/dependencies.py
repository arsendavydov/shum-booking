"""
Модуль зависимостей (Dependencies) для FastAPI.

Содержит все функции-зависимости для Dependency Injection:
- Пагинация
- Сессии базы данных
- Репозитории
- Сервисы
- JWT аутентификация
"""

from typing import Annotated, Any

from fastapi import Cookie, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.bookings import BookingsRepository
from src.repositories.hotels import HotelsRepository
from src.repositories.rooms import RoomsRepository
from src.repositories.users import UsersRepository
from src.schemas.users import SchemaUser
from src.services.auth import AuthService
from src.utils.db_manager import DBManager

# ============================================================================
# ПАГИНАЦИЯ
# ============================================================================


class PaginationParams(BaseModel):
    """Модель параметров пагинации."""

    page: int
    per_page: int


def get_pagination_params(
    page: Annotated[int, Query(ge=1, description="Номер страницы")] = 1,
    per_page: Annotated[int, Query(ge=1, le=20, description="Количество элементов на странице")] = 10,
) -> PaginationParams:
    """
    Dependency для получения параметров пагинации.

    Args:
        page: Номер страницы (по умолчанию 1, должно быть больше или равно 1)
        per_page: Количество элементов на странице (по умолчанию 10, должно быть от 1 до 20 включительно)

    Returns:
        PaginationParams с параметрами пагинации
    """
    return PaginationParams(page=page, per_page=per_page)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]


# ============================================================================
# СЕССИИ БАЗЫ ДАННЫХ
# ============================================================================


def get_db_manager() -> DBManager:
    """
    Dependency для получения экземпляра DBManager.

    Returns:
        DBManager: Экземпляр менеджера базы данных
    """
    return DBManager()


async def get_db() -> AsyncSession:
    """
    Dependency для получения сессии базы данных через DBManager.

    Использует DBManager как контекстный менеджер для управления сессией.
    FastAPI автоматически закроет сессию после завершения запроса.

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    async with get_db_manager() as db:
        yield db


DBDep = Annotated[AsyncSession, Depends(get_db)]


# ============================================================================
# РЕПОЗИТОРИИ - СОЗДАНИЕ ФУНКЦИЙ
# ============================================================================
# Для каждой сущности создаем две функции:
# 1. *_repository - для чтения (без commit)
# 2. *_repository_with_commit - для записи (с автоматическим commit/rollback)


async def get_hotels_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "HotelsRepository":
    """Dependency для получения репозитория отелей (только чтение)."""
    return DBManager.get_hotels_repository(db)


async def get_hotels_repository_with_commit(db: Annotated[AsyncSession, Depends(get_db)]) -> "HotelsRepository":
    """Dependency для получения репозитория отелей (запись с commit/rollback)."""
    repo = DBManager.get_hotels_repository(db)
    try:
        yield repo
        await DBManager.commit(db)
    except Exception:
        await DBManager.rollback(db)
        raise


async def get_users_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "UsersRepository":
    """Dependency для получения репозитория пользователей (только чтение)."""
    return DBManager.get_users_repository(db)


async def get_users_repository_with_commit(db: Annotated[AsyncSession, Depends(get_db)]) -> "UsersRepository":
    """Dependency для получения репозитория пользователей (запись с commit/rollback)."""
    repo = DBManager.get_users_repository(db)
    try:
        yield repo
        await DBManager.commit(db)
    except Exception:
        await DBManager.rollback(db)
        raise


async def get_rooms_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "RoomsRepository":
    """Dependency для получения репозитория комнат (только чтение)."""
    return DBManager.get_rooms_repository(db)


async def get_rooms_repository_with_commit(db: Annotated[AsyncSession, Depends(get_db)]) -> "RoomsRepository":
    """Dependency для получения репозитория комнат (запись с commit/rollback)."""
    repo = DBManager.get_rooms_repository(db)
    try:
        yield repo
        await DBManager.commit(db)
    except Exception:
        await DBManager.rollback(db)
        raise


# ============================================================================
# РЕПОЗИТОРИИ - АННОТАЦИИ ДЛЯ РОУТЕРОВ
# ============================================================================
# Эти аннотации позволяют использовать репозитории в роутерах с явной типизацией
# Пример: async def get_hotels(repo: HotelsRepositoryDep) -> List[SchemaHotel]

HotelsRepositoryDep = Annotated[HotelsRepository, Depends(get_hotels_repository)]
HotelsRepositoryDepWrite = Annotated[HotelsRepository, Depends(get_hotels_repository_with_commit)]

UsersRepositoryDep = Annotated[UsersRepository, Depends(get_users_repository)]
UsersRepositoryDepWrite = Annotated[UsersRepository, Depends(get_users_repository_with_commit)]

RoomsRepositoryDep = Annotated[RoomsRepository, Depends(get_rooms_repository)]
RoomsRepositoryDepWrite = Annotated[RoomsRepository, Depends(get_rooms_repository_with_commit)]


async def get_bookings_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "BookingsRepository":
    """Dependency для получения репозитория бронирований (только чтение)."""
    return DBManager.get_bookings_repository(db)


async def get_bookings_repository_with_commit(db: Annotated[AsyncSession, Depends(get_db)]) -> "BookingsRepository":
    """Dependency для получения репозитория бронирований (запись с commit/rollback)."""
    repo = DBManager.get_bookings_repository(db)
    try:
        yield repo
        await DBManager.commit(db)
    except Exception:
        await DBManager.rollback(db)
        raise


BookingsRepositoryDep = Annotated[BookingsRepository, Depends(get_bookings_repository)]
BookingsRepositoryDepWrite = Annotated[BookingsRepository, Depends(get_bookings_repository_with_commit)]


# ============================================================================
# СЕРВИСЫ
# ============================================================================


def get_auth_service() -> AuthService:
    """
    Dependency для получения экземпляра AuthService.

    Returns:
        Экземпляр AuthService
    """
    return AuthService()


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


# ============================================================================
# JWT АУТЕНТИФИКАЦИЯ
# ============================================================================
# Цепочка зависимостей для работы с JWT токенами:
# get_token → get_token_payload → get_current_user


async def get_token(
    request: Request, access_token: str | None = Cookie(None, alias="access_token", include_in_schema=False)
) -> str:
    """
    Dependency для получения JWT токена из запроса.

    Проверяет токен в cookie или Authorization header.

    Args:
        request: FastAPI Request объект
        access_token: JWT токен из cookie (опционально)

    Returns:
        str: JWT токен в виде строки

    Raises:
        HTTPException: 401 если токен не предоставлен
    """
    token = access_token

    # Если токена нет в cookie, проверяем Authorization header
    if not token:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split("Bearer ")[1]

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Токен доступа не предоставлен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


TokenDep = Annotated[str, Depends(get_token)]


async def get_token_payload(token: TokenDep, auth_service: AuthServiceDep) -> dict[str, Any]:
    """
    Dependency для получения и валидации payload из JWT токена.

    Декодирует токен и возвращает его payload.
    Использует get_token для получения токена.

    Args:
        token: JWT токен (получается через get_token)
        auth_service: Сервис для работы с JWT

    Returns:
        Dict[str, Any]: Payload токена

    Raises:
        HTTPException: 401 если токен невалиден или истек
    """
    payload = auth_service.decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Токен невалиден или истек",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


TokenPayloadDep = Annotated[dict[str, Any], Depends(get_token_payload)]


async def get_current_user(payload: TokenPayloadDep, db: DBDep) -> SchemaUser:
    """
    Dependency для получения текущего авторизованного пользователя.

    Использует валидированный payload токена для получения user_id
    и загрузки пользователя из БД.
    Использует get_token_payload (который использует get_token).

    Args:
        payload: Payload из JWT токена (получается через get_token_payload)
        db: Сессия базы данных

    Returns:
        SchemaUser: Данные текущего пользователя

    Raises:
        HTTPException: 401 если токен невалиден, отсутствует или пользователь не найден
    """
    # Получаем user_id из токена
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=401,
            detail="Токен не содержит идентификатор пользователя",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Невалидный идентификатор пользователя в токене",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Получаем пользователя из БД
    repo = DBManager.get_users_repository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


CurrentUserDep = Annotated[SchemaUser, Depends(get_current_user)]
