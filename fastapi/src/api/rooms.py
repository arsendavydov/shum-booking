from datetime import date

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from src.api.dependencies import DBDep, PaginationDep, RoomsServiceDep
from src.schemas import MessageResponse
from src.schemas.rooms import Room, RoomPATCH, SchemaRoom, SchemaRoomAvailable
from src.utils.api_helpers import get_or_404
from src.utils.db_manager import DBManager

router = APIRouter()

# Время жизни кэша для номеров (явно задано)
ROOMS_CACHE_TTL = 300  # 5 минут


@router.get(
    "",
    summary="Получить список номеров отеля",
    description="Возвращает список всех номеров указанного отеля с поддержкой пагинации. Поддерживает фильтрацию по title. Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=list[SchemaRoom],
)
@cache(expire=ROOMS_CACHE_TTL, namespace="rooms")
async def get_rooms(
    hotel_id: int,
    pagination: PaginationDep,
    db: DBDep,
    title: str | None = Query(
        default=None, description="Фильтр по названию номера (частичное совпадение, без учета регистра)"
    ),
) -> list[SchemaRoom]:
    """
    Получить список номеров отеля с поддержкой пагинации и фильтрации.

    Args:
        hotel_id: ID отеля
        pagination: Параметры пагинации (page и per_page)
        db: Сессия базы данных
        title: Опциональный фильтр по названию номера (частичное совпадение)

    Returns:
        Список номеров отеля с учетом пагинации и фильтров

    Raises:
        HTTPException: 404 если отель с указанным ID не найден
    """
    hotels_repo = DBManager.get_hotels_repository(db)
    await get_or_404(hotels_repo.get_by_id, hotel_id, "Отель")

    repo = DBManager.get_rooms_repository(db)
    rooms = await repo.get_paginated(page=pagination.page, per_page=pagination.per_page, hotel_id=hotel_id, title=title)
    return rooms


@router.get(
    "/available",
    summary="Получить список доступных номеров отеля на период",
    description="Возвращает список номеров отеля с количеством свободных номеров на указанный период (date_from - date_to). Поле quantity показывает количество свободных номеров.",
    response_model=list[SchemaRoomAvailable],
)
async def get_available_rooms(
    hotel_id: int,
    db: DBDep,
    date_from: date = Query(..., description="Дата начала периода (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Дата окончания периода (YYYY-MM-DD)"),
) -> list[SchemaRoomAvailable]:
    """
    Получить список доступных номеров отеля на указанный период.

    Args:
        hotel_id: ID отеля
        db: Сессия базы данных
        date_from: Дата начала периода
        date_to: Дата окончания периода

    Returns:
        Список номеров с количеством свободных номеров (quantity)

    Raises:
        HTTPException: 404 если отель не найден
        HTTPException: 400 если date_from >= date_to
    """
    # Валидация дат
    if date_from >= date_to:
        raise HTTPException(status_code=400, detail="Дата начала периода должна быть раньше даты окончания")

    hotels_repo = DBManager.get_hotels_repository(db)
    await get_or_404(hotels_repo.get_by_id, hotel_id, "Отель")

    repo = DBManager.get_rooms_repository(db)
    available_rooms = await repo.get_rooms_with_availability(hotel_id=hotel_id, date_from=date_from, date_to=date_to)

    return available_rooms


@router.get(
    "/{room_id}",
    summary="Получить номер по ID",
    description="Возвращает информацию о номере по указанному ID. Номер должен принадлежать указанному отелю. Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=SchemaRoom,
)
@cache(expire=ROOMS_CACHE_TTL, namespace="rooms")
async def get_room_by_id(hotel_id: int, room_id: int, db: DBDep) -> SchemaRoom:
    """
    Получить номер по ID.

    Args:
        hotel_id: ID отеля
        room_id: ID номера
        db: Сессия базы данных

    Returns:
        Информация о номере

    Raises:
        HTTPException: 404 если отель или номер не найдены, или номер не принадлежит отелю
    """
    hotels_repo = DBManager.get_hotels_repository(db)
    await get_or_404(hotels_repo.get_by_id, hotel_id, "Отель")

    repo = DBManager.get_rooms_repository(db)
    room = await repo.get_by_id(room_id)

    if room is None:
        raise HTTPException(status_code=404, detail="Номер не найден")

    if room.hotel_id != hotel_id:
        raise HTTPException(status_code=404, detail="Номер не принадлежит указанному отелю")

    return room


@router.post(
    "",
    summary="Создать новый номер",
    description="Создает новый номер в указанном отеле. ID генерируется автоматически. Можно сразу указать список ID удобств для добавления к номеру.",
    response_model=MessageResponse,
)
async def create_room(
    hotel_id: int,
    rooms_service: RoomsServiceDep,
    room: Room = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Создать стандартный номер",
                "description": "Создание стандартного номера с базовыми удобствами",
                "value": {
                    "title": "Стандартный номер",
                    "description": "Уютный стандартный номер с современным дизайном",
                    "price": 3000,
                    "quantity": 5,
                    "facility_ids": [120, 121, 122],
                },
            },
            "2": {
                "summary": "Создать люкс номер",
                "description": "Создание люкс номера с полным набором удобств",
                "value": {
                    "title": "Люкс",
                    "description": "Просторный люкс номер с видом на море",
                    "price": 8000,
                    "quantity": 2,
                    "facility_ids": [120, 121, 122, 123, 124, 129, 131],
                },
            },
        },
    ),
) -> MessageResponse:
    """
    Создать новый номер в отеле.

    Args:
        hotel_id: ID отеля
        room: Данные нового номера (включая опциональный список facility_ids)
        rooms_service: Сервис для работы с номерами

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если отель не найден или удобство не найдено
        HTTPException: 400 если передан невалидный ID удобства
    """
    async with DBManager.transaction(rooms_service.session):
        # Извлекаем facility_ids перед созданием комнаты
        facility_ids = room.facility_ids
        room_data = room.model_dump(exclude={"facility_ids"}, exclude_none=True)

        await rooms_service.create_room(hotel_id=hotel_id, room_data=room_data, facility_ids=facility_ids)

    # Инвалидируем кэш номеров
    await FastAPICache.clear(namespace="rooms")

    return MessageResponse(status="OK")


@router.put(
    "/{room_id}",
    summary="Полное обновление номера",
    description="Полностью обновляет информацию о номере по указанному ID. Номер должен принадлежать указанному отелю. Если передан facility_ids, эффективно обновляет связи удобств: удаляет только отсутствующие в новом списке, добавляет только новые, оставляет нетронутыми существующие.",
    response_model=MessageResponse,
)
async def update_room(
    hotel_id: int,
    room_id: int,
    rooms_service: RoomsServiceDep,
    room: Room = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Полное обновление номера",
                "description": "Обновление всех полей номера",
                "value": {
                    "title": "Улучшенный номер",
                    "description": "Обновленное описание номера",
                    "price": 4500,
                    "quantity": 4,
                    "facility_ids": [120, 121, 122, 123],
                },
            }
        },
    ),
) -> MessageResponse:
    """
    Полное обновление номера.

    Args:
        hotel_id: ID отеля
        room_id: ID номера для обновления
        rooms_service: Сервис для работы с номерами
        room: Данные для обновления (включая опциональный список facility_ids)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если отель или номер не найдены, или номер не принадлежит отелю
        HTTPException: 404 если удобство не найдено
    """
    async with DBManager.transaction(rooms_service.session):
        # Извлекаем facility_ids перед обновлением комнаты
        facility_ids = room.facility_ids
        room_data = room.model_dump(exclude={"facility_ids"}, exclude_none=True)

        await rooms_service.update_room(
            hotel_id=hotel_id, room_id=room_id, room_data=room_data, facility_ids=facility_ids
        )

    # Инвалидируем кэш номеров
    await FastAPICache.clear(namespace="rooms")

    return MessageResponse(status="OK")


@router.patch(
    "/{room_id}",
    summary="Частичное обновление номера",
    description="Частично обновляет информацию о номере по указанному ID. Номер должен принадлежать указанному отелю. Если передан facility_ids, эффективно обновляет связи удобств: удаляет только отсутствующие в новом списке, добавляет только новые, оставляет нетронутыми существующие.",
    response_model=MessageResponse,
)
async def partial_update_room(
    hotel_id: int,
    room_id: int,
    rooms_service: RoomsServiceDep,
    room: RoomPATCH = Body(
        ...,
        openapi_examples={
            "1": {"summary": "Обновить только цену", "value": {"price": 3500}},
            "2": {"summary": "Обновить количество", "value": {"quantity": 6}},
            "3": {
                "summary": "Обновить несколько полей",
                "value": {"title": "Премиум номер", "price": 5500, "facility_ids": [120, 121, 122, 123, 124]},
            },
        },
    ),
) -> MessageResponse:
    """
    Частичное обновление номера.

    Args:
        hotel_id: ID отеля
        room_id: ID номера для обновления
        room: Данные для обновления (опционально, включая facility_ids)
        rooms_service: Сервис для работы с номерами

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если отель или номер не найдены, или номер не принадлежит отелю
        HTTPException: 404 если удобство не найдено
    """
    async with DBManager.transaction(rooms_service.session):
        update_data = room.model_dump(exclude={"facility_ids"}, exclude_unset=True)

        await rooms_service.partial_update_room(hotel_id=hotel_id, room_id=room_id, room_data=update_data)

    # Инвалидируем кэш номеров
    await FastAPICache.clear(namespace="rooms")

    return MessageResponse(status="OK")


@router.delete(
    "/{room_id}",
    summary="Удалить номер",
    description="Удаляет номер по указанному ID. Номер должен принадлежать указанному отелю.",
    response_model=MessageResponse,
)
async def delete_room(hotel_id: int, room_id: int, rooms_service: RoomsServiceDep) -> MessageResponse:
    """
    Удалить номер.

    Args:
        hotel_id: ID отеля
        room_id: ID номера для удаления
        rooms_service: Сервис для работы с номерами

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если отель или номер не найдены, или номер не принадлежит отелю
    """
    async with DBManager.transaction(rooms_service.session):
        deleted = await rooms_service.delete_room(hotel_id=hotel_id, room_id=room_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Номер не найден")

    # Инвалидируем кэш номеров
    await FastAPICache.clear(namespace="rooms")

    return MessageResponse(status="OK")
