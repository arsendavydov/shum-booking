from fastapi import APIRouter, Body, HTTPException, Path, Query
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

from src.api.dependencies import DBDep, PaginationDep
from src.schemas import MessageResponse
from src.schemas.countries import Country, CountryPATCH, SchemaCountry
from src.utils.api_helpers import get_or_404, handle_validation_error
from src.utils.db_manager import DBManager

COUNTRIES_CACHE_TTL = 300

router = APIRouter()


@router.get(
    "",
    summary="Получить список стран",
    description="Возвращает список всех стран с поддержкой пагинации. Поддерживает фильтрацию по name (частичное совпадение, без учета регистра). Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=list[SchemaCountry],
)
@cache(expire=COUNTRIES_CACHE_TTL, namespace="countries")
async def get_countries(
    pagination: PaginationDep,
    db: DBDep,
    name: str | None = Query(
        default=None, description="Фильтр по названию страны (частичное совпадение, без учета регистра)"
    ),
) -> list[SchemaCountry]:
    """
    Получить список стран с поддержкой пагинации и фильтрации.

    Args:
        pagination: Параметры пагинации (page и per_page)
        db: Сессия базы данных
        name: Опциональный фильтр по названию страны (частичное совпадение)

    Returns:
        Список стран с учетом пагинации и фильтров
    """
    repo = DBManager.get_countries_repository(db)
    countries = await repo.get_paginated(page=pagination.page, per_page=pagination.per_page, name=name)
    return countries


@router.get(
    "/{country_id}",
    summary="Получить страну по ID",
    description="Возвращает информацию о стране по указанному ID. Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=SchemaCountry,
)
@cache(expire=COUNTRIES_CACHE_TTL, namespace="countries")
async def get_country_by_id(country_id: int = Path(..., description="ID страны"), db: DBDep = DBDep) -> SchemaCountry:
    """
    Получить страну по ID.

    Args:
        country_id: ID страны
        db: Сессия базы данных

    Returns:
        Информация о стране

    Raises:
        HTTPException: 404 если страна с указанным ID не найдена
    """
    repo = DBManager.get_countries_repository(db)
    country = await get_or_404(repo.get_by_id, country_id, "Страна")
    return country


@router.post(
    "",
    summary="Создать новую страну",
    description="Создает новую страну с указанным названием и ISO кодом. ID генерируется автоматически. Инвалидирует кэш стран.",
    response_model=MessageResponse,
)
async def create_country(
    db: DBDep,
    country: Country = Body(
        ..., openapi_examples={"1": {"summary": "Создать страну", "value": {"name": "Россия", "iso_code": "RU"}}}
    ),
) -> MessageResponse:
    """
    Создать новую страну.
    Инвалидирует кэш стран после создания.

    Args:
        db: Сессия базы данных
        country: Данные новой страны (name, iso_code)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 409 если страна с таким названием или ISO кодом уже существует
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_countries_repository(db)
        try:
            await repo.create_country_with_validation(name=country.name, iso_code=country.iso_code)
        except ValueError as e:
            raise handle_validation_error(e)

    # Инвалидируем кэш стран
    await FastAPICache.clear(namespace="countries")

    return MessageResponse(status="OK")


@router.put(
    "/{country_id}",
    summary="Полное обновление страны",
    description="Полностью обновляет информацию о стране по указанному ID. Требует передачи всех полей (name, iso_code). Инвалидирует кэш стран.",
    response_model=MessageResponse,
)
async def update_country(
    country_id: int = Path(..., description="ID страны"), db: DBDep = DBDep, country: Country = Body(...)
) -> MessageResponse:
    """
    Полное обновление страны.

    Args:
        country_id: ID страны для обновления
        db: Сессия базы данных
        country: Данные для обновления (name, iso_code обязательны)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если страна с указанным ID не найдена
        HTTPException: 409 если страна с таким названием или ISO кодом уже существует
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_countries_repository(db)
        try:
            await repo.update_country_with_validation(
                country_id=country_id, name=country.name, iso_code=country.iso_code
            )
        except ValueError as e:
            raise handle_validation_error(e)

    # Инвалидируем кэш стран
    await FastAPICache.clear(namespace="countries")

    return MessageResponse(status="OK")


@router.patch(
    "/{country_id}",
    summary="Частичное обновление страны",
    description="Частично обновляет информацию о стране по указанному ID. Можно обновить name, iso_code или их комбинацию. Инвалидирует кэш стран.",
    response_model=MessageResponse,
)
async def partial_update_country(
    country_id: int = Path(..., description="ID страны"), db: DBDep = DBDep, country: CountryPATCH = Body(...)
) -> MessageResponse:
    """
    Частичное обновление страны.

    Args:
        country_id: ID страны для обновления
        db: Сессия базы данных
        country: Данные для обновления (name, iso_code опциональны)

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если страна с указанным ID не найдена
        HTTPException: 409 если страна с таким названием или ISO кодом уже существует
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_countries_repository(db)
        try:
            await repo.partial_update_country_with_validation(
                country_id=country_id, name=country.name, iso_code=country.iso_code
            )
        except ValueError as e:
            raise handle_validation_error(e)

    # Инвалидируем кэш стран
    await FastAPICache.clear(namespace="countries")

    return MessageResponse(status="OK")


@router.delete(
    "/{country_id}",
    summary="Удалить страну",
    description="Удаляет страну по указанному ID. Возвращает статус 'OK' при успешном удалении. Инвалидирует кэш стран.",
    response_model=MessageResponse,
)
async def delete_country(country_id: int = Path(..., description="ID страны"), db: DBDep = DBDep) -> MessageResponse:
    """
    Удалить страну.
    Инвалидирует кэш стран после удаления.

    Args:
        country_id: ID страны для удаления
        db: Сессия базы данных

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если страна с указанным ID не найдена
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_countries_repository(db)
        try:
            deleted = await repo.delete(country_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not deleted:
            raise HTTPException(status_code=404, detail="Страна не найдена")

    # Инвалидируем кэш стран
    await FastAPICache.clear(namespace="countries")

    return MessageResponse(status="OK")
