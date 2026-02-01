from fastapi import APIRouter, Query, HTTPException, Body
from typing import List
from datetime import date
from fastapi_cache.decorator import cache
from src.schemas.hotels import Hotel, HotelPATCH, SchemaHotel, SchemaHotelWithRooms
from src.schemas import MessageResponse
from src.api import PaginationDep, DBDep, get_or_404, invalidate_cache, handle_delete_operation, handle_validation_error
from src.utils.db_manager import DBManager

router = APIRouter()

# Время жизни кэша для отелей (явно задано)
HOTELS_CACHE_TTL = 300  # 5 минут


@router.get(
    "",
    summary="Получить список отелей",
    description="Возвращает список отелей с поддержкой пагинации, фильтрации и сортировки. Поддерживает фильтрацию по title (частичное совпадение, без учета регистра), city (название города, частичное совпадение без учета регистра), city_id (точное совпадение). Поддерживает сортировку по id, title, city. Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=List[SchemaHotel]
)
@cache(expire=HOTELS_CACHE_TTL, namespace="hotels")
async def get_hotels(
    pagination: PaginationDep,
    db: DBDep,
    title: str | None = Query(default=None, description="Фильтр по названию отеля (частичное совпадение, без учета регистра)"),
    city: str | None = Query(default=None, description="Фильтр по названию города (частичное совпадение, без учета регистра)"),
    city_id: int | None = Query(default=None, description="Фильтр по ID города (точное совпадение)"),
    sort_by: str = Query(default="id", description="Поле для сортировки: id, title, city", pattern="^(id|title|city)$"),
    order: str = Query(default="asc", description="Направление сортировки: asc или desc", pattern="^(asc|desc)$")
) -> List[SchemaHotel]:
    """
    Получить список отелей с пагинацией, фильтрацией и сортировкой.
    
    Args:
        pagination: Параметры пагинации (page и per_page)
        db: Сессия базы данных
        title: Опциональный фильтр по названию отеля (частичное совпадение)
        city: Опциональный фильтр по названию города (частичное совпадение, без учета регистра)
        city_id: Опциональный фильтр по ID города (точное совпадение)
        sort_by: Поле для сортировки (id, title, city) - по умолчанию "id"
        order: Направление сортировки (asc, desc) - по умолчанию "asc"
        
    Returns:
        Список отелей с учетом пагинации, фильтров и сортировки
    """
    repo = DBManager.get_hotels_repository(db)
    hotels = await repo.get_paginated(
        page=pagination.page,
        per_page=pagination.per_page,
        title=title,
        city=city,
        city_id=city_id,
        sort_by=sort_by,
        order=order
    )
    return hotels


@router.get(
    "/rooms/available",
    summary="Получить отели с доступными комнатами на период",
    description="Возвращает список отелей с комнатами и актуальным количеством свободных номеров на указанный период с поддержкой пагинации и фильтрации. Поддерживает фильтрацию по полям отеля: title (частичное совпадение), city (название города, частичное совпадение без учета регистра). Если указан hotel_id, возвращается только указанный отель. В поле quantity каждой комнаты указывается количество свободных номеров на указанный период. Комнаты с quantity=0 не возвращаются.",
    response_model=List[SchemaHotelWithRooms]
)
async def get_hotels_with_available_rooms(
    pagination: PaginationDep,
    db: DBDep,
    date_from: date = Query(..., description="Дата начала периода (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Дата окончания периода (YYYY-MM-DD)"),
    hotel_id: int | None = Query(default=None, description="Опциональный ID отеля. Если указан, возвращается только этот отель."),
    title: str | None = Query(default=None, description="Фильтр по названию отеля (частичное совпадение, без учета регистра)"),
    city: str | None = Query(default=None, description="Фильтр по названию города (частичное совпадение, без учета регистра)")
) -> List[SchemaHotelWithRooms]:
    """
    Получить отели с доступными комнатами на указанный период с поддержкой пагинации и фильтрации.
    
    Для каждого отеля возвращается список комнат с актуальным количеством
    свободных номеров на указанный период. Комнаты с quantity=0 не возвращаются.
    
    Поддерживает фильтрацию по полям модели отеля:
    - title: частичное совпадение, без учета регистра (String)
    - city: частичное совпадение по названию города, без учета регистра (String)
    
    Args:
        pagination: Параметры пагинации (page и per_page)
        db: Сессия базы данных
        date_from: Дата начала периода (обязательно)
        date_to: Дата окончания периода (обязательно)
        hotel_id: Опциональный ID отеля. Если указан, возвращается только этот отель.
        title: Опциональный фильтр по названию отеля (частичное совпадение)
        city: Опциональный фильтр по названию города (частичное совпадение, без учета регистра)
        
    Returns:
        Список отелей с комнатами и актуальным количеством свободных номеров с учетом пагинации и фильтров
        
    Raises:
        HTTPException: 400 если даты некорректны (date_from >= date_to)
    """
    if date_from >= date_to:
        raise HTTPException(
            status_code=400,
            detail="Дата начала периода должна быть раньше даты окончания"
        )
    
    repo = DBManager.get_hotels_repository(db)
    hotels = await repo.get_hotels_with_available_rooms(
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        per_page=pagination.per_page,
        hotel_id=hotel_id,
        title=title,
        city=city
    )
    
    return hotels

@router.get(
    "/{hotel_id}",
    summary="Получить отель по ID",
    description="Возвращает информацию об отеле по указанному ID. Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=SchemaHotel
)
@cache(expire=HOTELS_CACHE_TTL, namespace="hotels")
async def get_hotel_by_id(
    hotel_id: int,
    db: DBDep
) -> SchemaHotel:
    """
    Получить отель по ID.
    
    Args:
        hotel_id: ID отеля
        db: Сессия базы данных
        
    Returns:
        Информация об отеле
        
    Raises:
        HTTPException: 404 если отель с указанным ID не найден
    """
    repo = DBManager.get_hotels_repository(db)
    hotel = await get_or_404(repo.get_by_id, hotel_id, "Отель")
    return hotel

@router.post(
    "",
    summary="Создать новый отель",
    description="Создает новый отель с указанным названием и местоположением. ID генерируется автоматически",
    response_model=MessageResponse
)
async def create_hotel(
    db: DBDep,
    hotel: Hotel = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Создать отель в Москве",
                "description": "Пример создания отеля в Москве (название города может быть в любом регистре)",
                "value": {
                    "title": "Гранд Отель Москва",
                    "city": "Москва",
                    "address": "Тверская улица, дом 3"
                }
            },
            "2": {
                "summary": "Создать отель в Дубае",
                "description": "Пример создания отеля в Дубае (название города может быть в любом регистре)",
                "value": {
                    "title": "Burj Al Arab",
                    "city": "дубай",
                    "address": "Jumeirah Street, 3"
                }
            }
        }
    )
) -> MessageResponse:
    """
    Создать новый отель.
    
    Args:
        db: Сессия базы данных
        hotel: Данные нового отеля (title, city, address)
        
    Returns:
        Словарь со статусом операции {"status": "OK"}
    """
    async with DBManager.transaction(db):
        hotels_repo = DBManager.get_hotels_repository(db)
        try:
            await hotels_repo.create_hotel_with_validation(
                title=hotel.title,
                city_name=hotel.city,
                address=hotel.address,
                postal_code=hotel.postal_code,
                check_in_time=hotel.check_in_time,
                check_out_time=hotel.check_out_time
            )
        except ValueError as e:
            raise handle_validation_error(e)
    
    # Инвалидируем кэш отелей
    await invalidate_cache("hotels")
    
    return MessageResponse(status="OK")

@router.put(
    "/{hotel_id}",
    summary="Полное обновление отеля",
    description="Полностью обновляет информацию об отеле по указанному ID. Требует передачи всех полей (title, city, address). Название города может быть в любом регистре.",
    response_model=MessageResponse
)
async def update_hotel(
    hotel_id: int,
    db: DBDep,
    hotel: Hotel = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Обновить отель",
                "value": {
                    "title": "Сочи Отель Обновленный",
                    "city": "Москва",
                    "address": "Краснодарский край, улица Ленина, 1"
                }
            }
        }
    )
) -> MessageResponse:
    """
    Полное обновление отеля.
    
    Args:
        hotel_id: ID отеля для обновления
        db: Сессия базы данных
        hotel: Данные для обновления (title, city, address обязательны)
        
    Returns:
        Словарь со статусом операции {"status": "OK"}
        
    Raises:
        HTTPException: 404 если отель с указанным ID не найден
    """
    async with DBManager.transaction(db):
        hotels_repo = DBManager.get_hotels_repository(db)
        try:
            await hotels_repo.update_hotel_with_validation(
                hotel_id=hotel_id,
                title=hotel.title,
                city_name=hotel.city,
                address=hotel.address,
                postal_code=hotel.postal_code,
                check_in_time=hotel.check_in_time,
                check_out_time=hotel.check_out_time
            )
        except ValueError as e:
            raise handle_validation_error(e)
    
    # Инвалидируем кэш отелей
    await invalidate_cache("hotels")
    
    return MessageResponse(status="OK")

@router.patch(
    "/{hotel_id}",
    summary="Частичное обновление отеля",
    description="Частично обновляет информацию об отеле по указанному ID. Можно обновить title, city, address или их комбинацию",
    response_model=MessageResponse
)
async def partial_update_hotel(
    hotel_id: int,
    db: DBDep,
    hotel: HotelPATCH = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Обновить только название",
                "value": {
                    "title": "Сочи Отель Премиум"
                }
            },
            "2": {
                "summary": "Обновить только адрес",
                "value": {
                    "address": "Краснодарский край, улица Ленина, 1"
                }
            },
            "3": {
                "summary": "Обновить несколько полей",
                "value": {
                    "title": "Сочи Отель Премиум",
                    "city": "москва",
                    "address": "Краснодарский край, улица Ленина, 1"
                }
            }
        }
    )
) -> MessageResponse:
    """
    Частичное обновление отеля.
    
    Args:
        hotel_id: ID отеля для обновления
        db: Сессия базы данных
        hotel: Данные для обновления (title, city, address - опционально)
        
    Returns:
        Словарь со статусом операции {"status": "OK"}
        
    Raises:
        HTTPException: 404 если отель с указанным ID не найден
    """
    async with DBManager.transaction(db):
        hotels_repo = DBManager.get_hotels_repository(db)
        try:
            update_data = hotel.model_dump(exclude_unset=True)
            await hotels_repo.partial_update_hotel_with_validation(
                hotel_id=hotel_id,
                title=update_data.get("title"),
                city_name=update_data.get("city"),
                address=update_data.get("address"),
                postal_code=update_data.get("postal_code"),
                check_in_time=update_data.get("check_in_time"),
                check_out_time=update_data.get("check_out_time")
            )
        except ValueError as e:
            raise handle_validation_error(e)
    
    # Инвалидируем кэш отелей
    await invalidate_cache("hotels")
    
    return MessageResponse(status="OK")

@router.delete("/{hotel_id}", summary="Удалить отель", description="Удаляет отель по указанному ID. Возвращает статус 'OK' при успешном удалении", response_model=MessageResponse)
async def delete_hotel(hotel_id: int, db: DBDep) -> MessageResponse:
    """
    Удалить отель.
    
    Args:
        hotel_id: ID отеля для удаления
        db: Сессия базы данных
        
    Returns:
        Словарь со статусом операции {"status": "OK"}
        
    Raises:
        HTTPException: 404 если отель с указанным ID не найден
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_hotels_repository(db)
        await handle_delete_operation(repo.delete, hotel_id, "Отель")
    
    # Инвалидируем кэш отелей и номеров (номера удаляются каскадно)
    await invalidate_cache("hotels")
    await invalidate_cache("rooms")
    
    return MessageResponse(status="OK")
