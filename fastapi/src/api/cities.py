from fastapi import APIRouter, Body, HTTPException, Path, Query
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from src.api import DBDep, PaginationDep
from src.schemas import MessageResponse
from src.schemas.cities import City, CityPATCH, SchemaCity
from src.utils.api_helpers import get_or_404, handle_validation_error
from src.utils.db_manager import DBManager

CITIES_CACHE_TTL = 300

router = APIRouter()


@router.get(
    "",
    summary="Получить список городов",
    description="Возвращает список всех городов с поддержкой пагинации. Поддерживает фильтрацию по name (частичное совпадение, без учета регистра) и country_id (точное совпадение). Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=list[SchemaCity],
)
@cache(expire=CITIES_CACHE_TTL, namespace="cities")
async def get_cities(
    pagination: PaginationDep,
    db: DBDep,
    name: str | None = Query(
        default=None, description="Фильтр по названию города (частичное совпадение, без учета регистра)"
    ),
    country_id: int | None = Query(default=None, description="Фильтр по ID страны (точное совпадение)"),
) -> list[SchemaCity]:
    """
    Получить список городов с поддержкой пагинации и фильтрации.

    Args:
        pagination: Параметры пагинации (page и per_page)
        db: Сессия базы данных
        name: Опциональный фильтр по названию города (частичное совпадение)
        country_id: Опциональный фильтр по ID страны (точное совпадение)

    Returns:
        Список городов с учетом пагинации и фильтров
    """
    repo = DBManager.get_cities_repository(db)
    cities = await repo.get_paginated(
        page=pagination.page, per_page=pagination.per_page, name=name, country_id=country_id
    )
    return cities


@router.get(
    "/{city_id}",
    summary="Получить город по ID",
    description="Возвращает информацию о городе по указанному ID. Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=SchemaCity,
)
@cache(expire=CITIES_CACHE_TTL, namespace="cities")
async def get_city_by_id(city_id: int = Path(..., description="ID города"), db: DBDep = DBDep) -> SchemaCity:
    """
    Получить город по ID.

    Args:
        city_id: ID города
        db: Сессия базы данных

    Returns:
        Информация о городе

    Raises:
        HTTPException: 404 если город с указанным ID не найден
    """
    repo = DBManager.get_cities_repository(db)
    city = await get_or_404(repo.get_by_id, city_id, "Город")
    return city


@router.post(
    "",
    summary="Создать новый город",
    description="Создает новый город с указанным названием и ID страны. ID генерируется автоматически. Инвалидирует кэш городов.",
    response_model=MessageResponse,
)
async def create_city(
    db: DBDep,
    city: City = Body(
        ..., openapi_examples={"1": {"summary": "Создать город", "value": {"name": "Москва", "country_id": 1}}}
    ),
) -> MessageResponse:
    """
    Создать новый город.
    Инвалидирует кэш городов после создания.

    Args:
        db: Сессия базы данных
        city: Данные нового города (name, country_id)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если страна с указанным ID не найдена
        HTTPException: 409 если город с таким названием в этой стране уже существует
    """
    async with DBManager.transaction(db):
        cities_repo = DBManager.get_cities_repository(db)
        try:
            await cities_repo.create_city_with_validation(name=city.name, country_id=city.country_id)
        except ValueError as e:
            raise handle_validation_error(e)

    # Инвалидируем кэш городов
    await FastAPICache.clear(namespace="cities")

    return MessageResponse(status="OK")


@router.put(
    "/{city_id}",
    summary="Полное обновление города",
    description="Полностью обновляет информацию о городе по указанному ID. Требует передачи всех полей (name, country_id). Инвалидирует кэш городов.",
    response_model=MessageResponse,
)
async def update_city(
    city_id: int = Path(..., description="ID города"), db: DBDep = DBDep, city: City = Body(...)
) -> MessageResponse:
    """
    Полное обновление города.

    Args:
        city_id: ID города для обновления
        db: Сессия базы данных
        city: Данные для обновления (name, country_id обязательны)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если город или страна не найдены
        HTTPException: 409 если город с таким названием в этой стране уже существует
    """
    async with DBManager.transaction(db):
        cities_repo = DBManager.get_cities_repository(db)
        try:
            await cities_repo.update_city_with_validation(city_id=city_id, name=city.name, country_id=city.country_id)
        except ValueError as e:
            raise handle_validation_error(e)

    # Инвалидируем кэш городов
    await FastAPICache.clear(namespace="cities")

    return MessageResponse(status="OK")


@router.patch(
    "/{city_id}",
    summary="Частичное обновление города",
    description="Частично обновляет информацию о городе по указанному ID. Можно обновить name, country_id или их комбинацию. Инвалидирует кэш городов.",
    response_model=MessageResponse,
)
async def partial_update_city(
    city_id: int = Path(..., description="ID города"), db: DBDep = DBDep, city: CityPATCH = Body(...)
) -> MessageResponse:
    """
    Частичное обновление города.

    Args:
        city_id: ID города для обновления
        db: Сессия базы данных
        city: Данные для обновления (name, country_id опциональны)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если город или страна не найдены
        HTTPException: 409 если город с таким названием в этой стране уже существует
    """
    async with DBManager.transaction(db):
        cities_repo = DBManager.get_cities_repository(db)
        try:
            update_data = city.model_dump(exclude_unset=True)
            await cities_repo.partial_update_city_with_validation(
                city_id=city_id, name=update_data.get("name"), country_id=update_data.get("country_id")
            )
        except ValueError as e:
            raise handle_validation_error(e)

    # Инвалидируем кэш городов
    await FastAPICache.clear(namespace="cities")

    return MessageResponse(status="OK")


@router.delete(
    "/{city_id}",
    summary="Удалить город",
    description="Удаляет город по указанному ID. Возвращает статус 'OK' при успешном удалении. Инвалидирует кэш городов.",
    response_model=MessageResponse,
)
async def delete_city(city_id: int = Path(..., description="ID города"), db: DBDep = DBDep) -> MessageResponse:
    """
    Удалить город.
    Инвалидирует кэш городов после удаления.

    Args:
        city_id: ID города для удаления
        db: Сессия базы данных

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если город с указанным ID не найден
    """
    async with DBManager.transaction(db):
        cities_repo = DBManager.get_cities_repository(db)
        try:
            deleted = await cities_repo.delete(city_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not deleted:
            raise HTTPException(status_code=404, detail="Город не найден")

    # Инвалидируем кэш городов
    await FastAPICache.clear(namespace="cities")

    return MessageResponse(status="OK")
