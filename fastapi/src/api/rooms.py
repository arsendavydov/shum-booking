from datetime import date

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from src.api import DBDep, PaginationDep, RoomsRepositoryDepWrite
from src.schemas import MessageResponse
from src.utils.api_helpers import get_or_404
from src.schemas.rooms import Room, RoomPATCH, SchemaRoom, SchemaRoomAvailable
from src.utils.db_manager import DBManager

router = APIRouter()

# Время жизни кэша для номеров (явно задано)
ROOMS_CACHE_TTL = 300  # 5 минут


async def validate_and_process_facilities(
    db: DBDep, room_id: int, facility_ids: list[int] | None, rooms_repo: RoomsRepositoryDepWrite, is_update: bool = False
) -> None:
    """
    Валидировать существование удобств и обработать их для комнаты.

    Args:
        db: Сессия базы данных
        room_id: ID комнаты
        facility_ids: Список ID удобств для обработки (может быть None)
        rooms_repo: Репозиторий комнат
        is_update: Если True, использует эффективное обновление. Если False, добавляет новые связи.

    Raises:
        HTTPException: 404 если какое-либо удобство не найдено
        HTTPException: 400 если произошла ошибка при обработке
    """
    # Если facility_ids is None, ничего не делаем (оставляем существующие связи)
    # Если facility_ids = [], это означает очистку всех связей (для PUT/PATCH)
    if facility_ids is None:
        return

    # Если передан пустой список и это обновление, очищаем все связи
    if is_update and len(facility_ids) == 0:
        await rooms_repo.update_room_facilities(room_id, [])
        return

    facilities_repo = DBManager.get_facilities_repository(db)

    # Проверяем существование всех удобств
    for facility_id in facility_ids:
        facility = await facilities_repo.get_by_id(facility_id)
        if facility is None:
            raise HTTPException(status_code=404, detail=f"Удобство с ID {facility_id} не найдено")

    # Обрабатываем связи
    try:
        if is_update:
            # Эффективное обновление: удаляет только отсутствующие, добавляет только новые
            await rooms_repo.update_room_facilities(room_id, facility_ids)
        else:
            # Добавление новых связей
            for facility_id in facility_ids:
                await rooms_repo.add_facility(room_id, facility_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
async def create_room(hotel_id: int, db: DBDep, room: Room = Body(...)) -> MessageResponse:
    """
    Создать новый номер в отеле.

    Args:
        hotel_id: ID отеля
        db: Сессия базы данных
        room: Данные нового номера (включая опциональный список facility_ids)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если отель не найден или удобство не найдено
        HTTPException: 400 если передан невалидный ID удобства
    """
    async with DBManager.transaction(db):
        hotels_repo = DBManager.get_hotels_repository(db)
        hotel = await hotels_repo.get_by_id(hotel_id)
        if hotel is None:
            raise HTTPException(status_code=404, detail="Отель не найден")

        repo = DBManager.get_rooms_repository(db)

        # Извлекаем facility_ids перед созданием комнаты
        facility_ids = room.facility_ids
        room_data = room.model_dump(exclude={"facility_ids"}, exclude_none=True)
        room_data["hotel_id"] = hotel_id

        # Создаем комнату
        created_room_schema = await repo.create(**room_data)
        room_id = created_room_schema.id

        # Если передан список удобств, добавляем их к комнате
        await validate_and_process_facilities(
            db=db, room_id=room_id, facility_ids=facility_ids, rooms_repo=repo, is_update=False
        )

    # Инвалидируем кэш номеров
    await FastAPICache.clear(namespace="rooms")

    return MessageResponse(status="OK")


@router.put(
    "/{room_id}",
    summary="Полное обновление номера",
    description="Полностью обновляет информацию о номере по указанному ID. Номер должен принадлежать указанному отелю. Если передан facility_ids, эффективно обновляет связи удобств: удаляет только отсутствующие в новом списке, добавляет только новые, оставляет нетронутыми существующие.",
    response_model=MessageResponse,
)
async def update_room(hotel_id: int, room_id: int, db: DBDep, room: Room = Body(...)) -> MessageResponse:
    """
    Полное обновление номера.

    Args:
        hotel_id: ID отеля
        room_id: ID номера для обновления
        db: Сессия базы данных
        room: Данные для обновления (включая опциональный список facility_ids)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если отель или номер не найдены, или номер не принадлежит отелю
        HTTPException: 404 если удобство не найдено
    """
    async with DBManager.transaction(db):
        hotels_repo = DBManager.get_hotels_repository(db)
        await get_or_404(hotels_repo.get_by_id, hotel_id, "Отель")

        repo = DBManager.get_rooms_repository(db)
        existing_room = await get_or_404(repo.get_by_id, room_id, "Номер")

        if existing_room.hotel_id != hotel_id:
            raise HTTPException(status_code=404, detail="Номер не принадлежит указанному отелю")

        # Извлекаем facility_ids перед обновлением комнаты
        facility_ids = room.facility_ids
        room_data = room.model_dump(exclude={"facility_ids"}, exclude_none=True)
        room_data["hotel_id"] = hotel_id

        try:
            updated_room = await repo.edit(id=room_id, **room_data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if updated_room is None:
            raise HTTPException(status_code=404, detail="Номер не найден")

        # Обновляем связи удобств (если facility_ids передан, даже если это пустой список)
        # Если facility_ids is None, оставляем существующие связи без изменений
        if facility_ids is not None:
            await validate_and_process_facilities(
                db=db, room_id=room_id, facility_ids=facility_ids, rooms_repo=repo, is_update=True
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
async def partial_update_room(hotel_id: int, room_id: int, db: DBDep, room: RoomPATCH = Body(...)) -> MessageResponse:
    """
    Частичное обновление номера.

    Args:
        hotel_id: ID отеля
        room_id: ID номера для обновления
        db: Сессия базы данных
        room: Данные для обновления (опционально, включая facility_ids)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если отель или номер не найдены, или номер не принадлежит отелю
        HTTPException: 404 если удобство не найдено
    """
    async with DBManager.transaction(db):
        hotels_repo = DBManager.get_hotels_repository(db)
        hotel = await hotels_repo.get_by_id(hotel_id)
        if hotel is None:
            raise HTTPException(status_code=404, detail="Отель не найден")

        repo = DBManager.get_rooms_repository(db)
        existing_room = await repo.get_by_id(room_id)
        if existing_room is None:
            raise HTTPException(status_code=404, detail="Номер не найден")

        if existing_room.hotel_id != hotel_id:
            raise HTTPException(status_code=404, detail="Номер не принадлежит указанному отелю")

        # Извлекаем facility_ids перед обновлением комнаты
        facility_ids = room.facility_ids
        update_data = room.model_dump(exclude={"facility_ids"}, exclude_unset=True)

        # Обновляем только переданные поля (кроме facility_ids)
        if update_data:
            await repo.update(id=room_id, **update_data)

        # Если передан список удобств, эффективно обновляем связи
        await validate_and_process_facilities(
            db=db, room_id=room_id, facility_ids=facility_ids, rooms_repo=repo, is_update=True
        )

    # Инвалидируем кэш номеров
    await FastAPICache.clear(namespace="rooms")

    return MessageResponse(status="OK")


@router.delete(
    "/{room_id}",
    summary="Удалить номер",
    description="Удаляет номер по указанному ID. Номер должен принадлежать указанному отелю.",
    response_model=MessageResponse,
)
async def delete_room(hotel_id: int, room_id: int, db: DBDep) -> MessageResponse:
    """
    Удалить номер.

    Args:
        hotel_id: ID отеля
        room_id: ID номера для удаления
        db: Сессия базы данных

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если отель или номер не найдены, или номер не принадлежит отелю
    """
    async with DBManager.transaction(db):
        hotels_repo = DBManager.get_hotels_repository(db)
        hotel = await hotels_repo.get_by_id(hotel_id)
        if hotel is None:
            raise HTTPException(status_code=404, detail="Отель не найден")

        repo = DBManager.get_rooms_repository(db)
        existing_room = await repo.get_by_id(room_id)
        if existing_room is None:
            raise HTTPException(status_code=404, detail="Номер не найден")

        if existing_room.hotel_id != hotel_id:
            raise HTTPException(status_code=404, detail="Номер не принадлежит указанному отелю")

        try:
            deleted = await repo.delete(room_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not deleted:
            raise HTTPException(status_code=404, detail="Номер не найден")

    # Инвалидируем кэш номеров
    await FastAPICache.clear(namespace="rooms")

    return MessageResponse(status="OK")
