from fastapi import APIRouter, Body, HTTPException

from src.api.dependencies import BookingsServiceDep, CurrentUserDep, PaginationDep
from src.metrics.collectors import bookings_created_total
from src.metrics.helpers import should_collect_metrics
from src.schemas import MessageResponse
from src.schemas.bookings import Booking, SchemaBooking
from src.utils.db_manager import DBManager

router = APIRouter()


@router.get(
    "",
    summary="Получить список всех бронирований",
    description="Возвращает список всех бронирований с поддержкой пагинации",
    response_model=list[SchemaBooking],
)
async def get_bookings(pagination: PaginationDep, bookings_service: BookingsServiceDep) -> list[SchemaBooking]:
    """
    Получить список всех бронирований с поддержкой пагинации.

    Args:
        pagination: Параметры пагинации (page и per_page)
        bookings_service: Сервис для работы с бронированиями

    Returns:
        Список всех бронирований с учетом пагинации
    """
    return await bookings_service.get_all_bookings(page=pagination.page, per_page=pagination.per_page)


@router.get(
    "/me",
    summary="Получить свои бронирования",
    description="Возвращает список бронирований текущего авторизованного пользователя с поддержкой пагинации. Требуется аутентификация через JWT токен.",
    response_model=list[SchemaBooking],
)
async def get_my_bookings(
    pagination: PaginationDep, current_user: CurrentUserDep, bookings_service: BookingsServiceDep
) -> list[SchemaBooking]:
    """
    Получить список бронирований текущего авторизованного пользователя.

    Args:
        pagination: Параметры пагинации (page и per_page)
        current_user: Текущий авторизованный пользователь (из JWT токена)
        bookings_service: Сервис для работы с бронированиями

    Returns:
        Список бронирований текущего пользователя с учетом пагинации

    Raises:
        HTTPException: 401 если пользователь не аутентифицирован
    """
    return await bookings_service.get_user_bookings(
        user_id=current_user.id, page=pagination.page, per_page=pagination.per_page
    )


@router.post(
    "",
    summary="Создать бронирование",
    description="Создает новое бронирование номера текущим авторизованным пользователем на указанные даты. Требуется аутентификация через JWT токен.",
    response_model=MessageResponse,
)
async def create_booking(
    current_user: CurrentUserDep,
    bookings_service: BookingsServiceDep,
    booking: Booking = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Создать бронирование на 3 ночи",
                "description": "Бронирование номера на период с завтрашнего дня на 3 ночи",
                "value": {"room_id": 508, "date_from": "2026-02-15", "date_to": "2026-02-18"},
            },
            "2": {
                "summary": "Создать бронирование на неделю",
                "description": "Бронирование номера на неделю",
                "value": {"room_id": 523, "date_from": "2026-03-01", "date_to": "2026-03-08"},
            },
        },
    ),
) -> MessageResponse:
    """
    Создать новое бронирование.

    Цена рассчитывается автоматически на основе цены номера за ночь
    и количества ночей (date_to - date_from).
    user_id берется из JWT токена (текущий авторизованный пользователь).

    Args:
        current_user: Текущий авторизованный пользователь (из JWT токена)
        booking: Данные бронирования (room_id, date_from, date_to)
        bookings_service: Сервис для работы с бронированиями

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 401 если пользователь не аутентифицирован
        HTTPException: 404 если номер не найден
        HTTPException: 400 если даты некорректны (date_from >= date_to)
        HTTPException: 409 если номер уже забронирован на указанные даты
    """
    async with DBManager.transaction(bookings_service.session):
        await bookings_service.create_booking(
            room_id=booking.room_id,
            user_id=current_user.id,
            date_from=booking.date_from,
            date_to=booking.date_to,
        )

    if should_collect_metrics():
        bookings_created_total.inc()

    return MessageResponse(status="OK")


@router.delete(
    "/{booking_id}",
    summary="Удалить бронирование",
    description="Удаляет бронирование по указанному ID. Пользователь может удалить только свои бронирования. Требуется аутентификация через JWT токен.",
    response_model=MessageResponse,
)
async def delete_booking(
    booking_id: int, current_user: CurrentUserDep, bookings_service: BookingsServiceDep
) -> MessageResponse:
    """
    Удалить бронирование.

    Пользователь может удалить только свои бронирования.
    user_id берется из JWT токена (текущий авторизованный пользователь).

    Args:
        booking_id: ID бронирования для удаления
        current_user: Текущий авторизованный пользователь (из JWT токена)
        bookings_service: Сервис для работы с бронированиями

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 401 если пользователь не аутентифицирован
        HTTPException: 404 если бронирование не найдено
        HTTPException: 403 если пользователь пытается удалить чужое бронирование
    """
    async with DBManager.transaction(bookings_service.session):
        deleted = await bookings_service.delete_booking(booking_id=booking_id, user_id=current_user.id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Бронирование не найдено")

    return MessageResponse(status="OK")
