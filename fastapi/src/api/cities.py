from fastapi import APIRouter, Query, HTTPException, Body, Path
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache
from src.schemas.cities import City, CityPATCH, SchemaCity
from src.schemas import MessageResponse
from src.api import PaginationDep, DBDep, get_or_404
from src.utils.db_manager import DBManager

CITIES_CACHE_TTL = 300

router = APIRouter()


@router.get(
    "",
    summary="Получить список городов",
    description="Возвращает список всех городов с поддержкой пагинации. Поддерживает фильтрацию по name (частичное совпадение, без учета регистра) и country_id (точное совпадение). Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=List[SchemaCity]
)
@cache(expire=CITIES_CACHE_TTL, namespace="cities")
async def get_cities(
    pagination: PaginationDep,
    db: DBDep,
    name: str | None = Query(default=None, description="Фильтр по названию города (частичное совпадение, без учета регистра)"),
    country_id: int | None = Query(default=None, description="Фильтр по ID страны (точное совпадение)")
) -> List[SchemaCity]:
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
        page=pagination.page,
        per_page=pagination.per_page,
        name=name,
        country_id=country_id
    )
    return cities


@router.get(
    "/{city_id}",
    summary="Получить город по ID",
    description="Возвращает информацию о городе по указанному ID. Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=SchemaCity
)
@cache(expire=CITIES_CACHE_TTL, namespace="cities")
async def get_city_by_id(
    city_id: int = Path(..., description="ID города"),
    db: DBDep = DBDep
) -> SchemaCity:
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
    response_model=MessageResponse
)
async def create_city(
    db: DBDep,
    city: City = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Создать город",
                "value": {
                    "name": "Москва",
                    "country_id": 1
                }
            }
        }
    )
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
        # Проверяем существование страны
        countries_repo = DBManager.get_countries_repository(db)
        country = await countries_repo._get_one_by_id_exact(city.country_id)
        if country is None:
            raise HTTPException(
                status_code=404,
                detail=f"Страна с ID {city.country_id} не найдена"
            )
        
        # Проверяем уникальность города в стране
        cities_repo = DBManager.get_cities_repository(db)
        existing_city = await cities_repo.get_by_name_and_country_id(city.name, city.country_id)
        if existing_city is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Город '{city.name}' в стране с ID {city.country_id} уже существует"
            )
        
        await cities_repo.create(name=city.name, country_id=city.country_id)
    
    # Инвалидируем кэш городов
    await FastAPICache.clear(namespace="cities")
    
    return MessageResponse(status="OK")


@router.put(
    "/{city_id}",
    summary="Полное обновление города",
    description="Полностью обновляет информацию о городе по указанному ID. Требует передачи всех полей (name, country_id). Инвалидирует кэш городов.",
    response_model=MessageResponse
)
async def update_city(
    city_id: int = Path(..., description="ID города"),
    db: DBDep = DBDep,
    city: City = Body(...)
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
        
        # Проверяем существование города
        existing_city = await cities_repo._get_one_by_id_exact(city_id)
        if existing_city is None:
            raise HTTPException(status_code=404, detail="Город не найден")
        
        # Проверяем существование страны
        countries_repo = DBManager.get_countries_repository(db)
        country = await countries_repo._get_one_by_id_exact(city.country_id)
        if country is None:
            raise HTTPException(
                status_code=404,
                detail=f"Страна с ID {city.country_id} не найдена"
            )
        
        # Проверяем уникальность города в стране, если изменяется name или country_id
        if city.name != existing_city.name or city.country_id != existing_city.country_id:
            existing_city_check = await cities_repo.get_by_name_and_country_id(city.name, city.country_id)
            if existing_city_check is not None and existing_city_check.id != city_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Город '{city.name}' в стране с ID {city.country_id} уже существует"
                )
        
        updated_city = await cities_repo.edit(
            id=city_id,
            name=city.name,
            country_id=city.country_id
        )
        
        if updated_city is None:
            raise HTTPException(status_code=404, detail="Город не найден")
    
    # Инвалидируем кэш городов
    await FastAPICache.clear(namespace="cities")
    
    return MessageResponse(status="OK")


@router.patch(
    "/{city_id}",
    summary="Частичное обновление города",
    description="Частично обновляет информацию о городе по указанному ID. Можно обновить name, country_id или их комбинацию. Инвалидирует кэш городов.",
    response_model=MessageResponse
)
async def partial_update_city(
    city_id: int = Path(..., description="ID города"),
    db: DBDep = DBDep,
    city: CityPATCH = Body(...)
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
        
        # Проверяем существование города с загрузкой связи country
        query = select(cities_repo.model).options(
            selectinload(cities_repo.model.country)
        ).where(cities_repo.model.id == city_id)
        result = await db.execute(query)
        existing_city_orm = result.scalar_one_or_none()
        
        if existing_city_orm is None:
            raise HTTPException(status_code=404, detail="Город не найден")
        
        # Получаем существующий город как схему для удобства
        existing_city = cities_repo._to_schema(existing_city_orm)
        
        # Формируем данные для обновления (только переданные поля)
        update_data = city.model_dump(exclude_unset=True)
        
        if not update_data:
            return MessageResponse(status="OK")
        
        # Проверяем и валидируем country_id, если указан
        if "country_id" in update_data:
            countries_repo = DBManager.get_countries_repository(db)
            country = await countries_repo._get_one_by_id_exact(update_data["country_id"])
            if country is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Страна с ID {update_data['country_id']} не найдена"
                )
        
        # Проверяем уникальность города в стране
        final_name = update_data.get("name", existing_city.name)
        final_country_id = update_data.get("country_id", existing_city.country_id)
        
        # Проверяем, изменилось ли что-то, что требует проверки уникальности
        if final_name != existing_city.name or final_country_id != existing_city.country_id:
            try:
                existing_city_check = await cities_repo.get_by_name_and_country_id(final_name, final_country_id)
                if existing_city_check is not None and existing_city_check.id != city_id:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Город '{final_name}' в стране с ID {final_country_id} уже существует"
                    )
            except Exception as e:
                # Если ошибка при проверке уникальности, пробрасываем дальше
                raise
        
        # Обновляем город
        updated_city = await cities_repo.edit(id=city_id, **update_data)
        
        if updated_city is None:
            raise HTTPException(status_code=404, detail="Город не найден")
    
    # Инвалидируем кэш городов
    await FastAPICache.clear(namespace="cities")
    
    return MessageResponse(status="OK")


@router.delete(
    "/{city_id}",
    summary="Удалить город",
    description="Удаляет город по указанному ID. Возвращает статус 'OK' при успешном удалении. Инвалидирует кэш городов.",
    response_model=MessageResponse
)
async def delete_city(
    city_id: int = Path(..., description="ID города"),
    db: DBDep = DBDep
) -> MessageResponse:
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

