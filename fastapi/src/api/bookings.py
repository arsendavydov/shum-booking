from fastapi import APIRouter, HTTPException, Body
from typing import List
from src.schemas.bookings import Booking, SchemaBooking
from src.schemas import MessageResponse
from src.api import DBDep, CurrentUserDep, PaginationDep, handle_validation_error
from src.utils.db_manager import DBManager

router = APIRouter()


@router.get(
    "",
    summary="Получить список всех бронирований",
    description="Возвращает список всех бронирований с поддержкой пагинации",
    response_model=List[SchemaBooking]
)
async def get_bookings(
    pagination: PaginationDep,
    db: DBDep
) -> List[SchemaBooking]:
    """
    Получить список всех бронирований с поддержкой пагинации.
    
    Args:
        pagination: Параметры пагинации (page и per_page)
        db: Сессия базы данных
        
    Returns:
        Список всех бронирований с учетом пагинации
    """
    repo = DBManager.get_bookings_repository(db)
    bookings = await repo.get_paginated(
        page=pagination.page,
        per_page=pagination.per_page
    )
    return bookings


@router.get(
    "/me",
    summary="Получить свои бронирования",
    description="Возвращает список бронирований текущего авторизованного пользователя с поддержкой пагинации. Требуется аутентификация через JWT токен.",
    response_model=List[SchemaBooking]
)
async def get_my_bookings(
    pagination: PaginationDep,
    db: DBDep,
    current_user: CurrentUserDep
) -> List[SchemaBooking]:
    """
    Получить список бронирований текущего авторизованного пользователя.
    
    Args:
        pagination: Параметры пагинации (page и per_page)
        db: Сессия базы данных
        current_user: Текущий авторизованный пользователь (из JWT токена)
        
    Returns:
        Список бронирований текущего пользователя с учетом пагинации
        
    Raises:
        HTTPException: 401 если пользователь не аутентифицирован
    """
    repo = DBManager.get_bookings_repository(db)
    bookings = await repo.get_paginated(
        page=pagination.page,
        per_page=pagination.per_page,
        user_id=current_user.id
    )
    return bookings


@router.post(
    "",
    summary="Создать бронирование",
    description="Создает новое бронирование номера текущим авторизованным пользователем на указанные даты. Требуется аутентификация через JWT токен.",
    response_model=MessageResponse
)
async def create_booking(
    db: DBDep,
    current_user: CurrentUserDep,
    booking: Booking = Body(...)
) -> MessageResponse:
    """
    Создать новое бронирование.
    
    Цена рассчитывается автоматически на основе цены номера за ночь
    и количества ночей (date_to - date_from).
    user_id берется из JWT токена (текущий авторизованный пользователь).
    
    Args:
        db: Сессия базы данных
        current_user: Текущий авторизованный пользователь (из JWT токена)
        booking: Данные бронирования (room_id, date_from, date_to)
        
    Returns:
        Словарь со статусом операции {"status": "OK"}
        
    Raises:
        HTTPException: 401 если пользователь не аутентифицирован
        HTTPException: 404 если номер не найден
        HTTPException: 400 если даты некорректны (date_from >= date_to)
        HTTPException: 409 если номер уже забронирован на указанные даты
    """
    async with DBManager.transaction(db):
        bookings_repo = DBManager.get_bookings_repository(db)
        try:
            await bookings_repo.create_booking_with_validation(
                room_id=booking.room_id,
                user_id=current_user.id,
                date_from=booking.date_from,
                date_to=booking.date_to
            )
        except ValueError as e:
            raise handle_validation_error(e)
    
    return MessageResponse(status="OK")


@router.delete(
    "/{booking_id}",
    summary="Удалить бронирование",
    description="Удаляет бронирование по указанному ID. Пользователь может удалить только свои бронирования. Требуется аутентификация через JWT токен.",
    response_model=MessageResponse
)
async def delete_booking(
    booking_id: int,
    db: DBDep,
    current_user: CurrentUserDep
) -> MessageResponse:
    """
    Удалить бронирование.
    
    Пользователь может удалить только свои бронирования.
    user_id берется из JWT токена (текущий авторизованный пользователь).
    
    Args:
        booking_id: ID бронирования для удаления
        db: Сессия базы данных
        current_user: Текущий авторизованный пользователь (из JWT токена)
        
    Returns:
        Словарь со статусом операции {"status": "OK"}
        
    Raises:
        HTTPException: 401 если пользователь не аутентифицирован
        HTTPException: 404 если бронирование не найдено
        HTTPException: 403 если пользователь пытается удалить чужое бронирование
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_bookings_repository(db)
        
        # Проверяем существование бронирования и принадлежность пользователю
        booking = await repo.get_by_id(booking_id)
        if booking is None:
            raise HTTPException(status_code=404, detail="Бронирование не найдено")
        
        # Проверяем, что бронирование принадлежит текущему пользователю
        if booking.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав для удаления этого бронирования"
            )
        
        try:
            deleted = await repo.delete(booking_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Бронирование не найдено")
    
    return MessageResponse(status="OK")

