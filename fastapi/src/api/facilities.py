from fastapi import APIRouter, Query, HTTPException, Body, Path
from typing import List
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache
from src.schemas.facilities import Facility, SchemaFacility
from src.schemas import MessageResponse
from src.api import PaginationDep, DBDep, get_or_404
from src.utils.db_manager import DBManager
# Время жизни кэша для facilities (явно задано)
# Если не задать expire в декораторе @cache, будет использоваться значение по умолчанию библиотеки (обычно None - кэш не истекает)
FACILITIES_CACHE_TTL = 300 

router = APIRouter()


@router.get(
    "",
    summary="Получить список удобств",
    description="Возвращает список всех удобств с поддержкой пагинации. Поддерживает фильтрацию по title (частичное совпадение, без учета регистра). Результаты кэшируются в Redis на 300 секунд (5 минут).",
    response_model=List[SchemaFacility]
)
@cache(expire=FACILITIES_CACHE_TTL, namespace="facilities")  # Время жизни кэша: 300 секунд (5 минут) - явно задано
async def get_facilities(
    pagination: PaginationDep,
    db: DBDep,
    title: str | None = Query(default=None, description="Фильтр по названию удобства (частичное совпадение, без учета регистра)")
) -> List[SchemaFacility]:
    """
    Получить список удобств с поддержкой пагинации и фильтрации.
    Использует кэширование в Redis для оптимизации производительности.
    
    Args:
        pagination: Параметры пагинации (page и per_page)
        db: Сессия базы данных
        title: Опциональный фильтр по названию удобства (частичное совпадение)
        
    Returns:
        Список удобств с учетом пагинации и фильтров
    """
    repo = DBManager.get_facilities_repository(db)
    facilities = await repo.get_paginated(
        page=pagination.page,
        per_page=pagination.per_page,
        title=title
    )
    return facilities


@router.get(
    "/{facility_id}",
    summary="Получить удобство по ID",
    description="Возвращает информацию об удобстве по указанному ID",
    response_model=SchemaFacility
)
async def get_facility_by_id(
    facility_id: int = Path(..., description="ID удобства"),
    db: DBDep = DBDep
) -> SchemaFacility:
    """
    Получить удобство по ID.
    
    Args:
        facility_id: ID удобства
        db: Сессия базы данных
        
    Returns:
        Информация об удобстве
        
    Raises:
        HTTPException: 404 если удобство с указанным ID не найдено
    """
    repo = DBManager.get_facilities_repository(db)
    facility = await get_or_404(repo.get_by_id, facility_id, "Удобство")
    return facility


@router.post(
    "",
    summary="Создать новое удобство",
    description="Создает новое удобство с указанным названием. ID генерируется автоматически. Инвалидирует кэш удобств.",
    response_model=MessageResponse
)
async def create_facility(
    db: DBDep,
    facility: Facility = Body(
        ...,
        openapi_examples={
            "1": {
                "summary": "Создать удобство",
                "value": {
                    "title": "Wi-Fi"
                }
            }
        }
    )
) -> MessageResponse:
    """
    Создать новое удобство.
    Инвалидирует кэш удобств после создания.
    
    Args:
        db: Сессия базы данных
        facility: Данные нового удобства (title)
        
    Returns:
        Словарь со статусом операции {"status": "OK"}
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_facilities_repository(db)
        await repo.create(title=facility.title)
    
    # Инвалидируем кэш удобств
    await FastAPICache.clear(namespace="facilities")
    
    return MessageResponse(status="OK")


@router.delete(
    "/{facility_id}",
    summary="Удалить удобство",
    description="Удаляет удобство по указанному ID. Возвращает статус 'OK' при успешном удалении. Инвалидирует кэш удобств.",
    response_model=MessageResponse
)
async def delete_facility(
    facility_id: int = Path(..., description="ID удобства"),
    db: DBDep = DBDep
) -> MessageResponse:
    """
    Удалить удобство.
    Инвалидирует кэш удобств после удаления.
    
    Args:
        facility_id: ID удобства для удаления
        db: Сессия базы данных
        
    Returns:
        Словарь со статусом операции {"status": "OK"}
        
    Raises:
        HTTPException: 404 если удобство с указанным ID не найдено
    """
    async with DBManager.transaction(db):
        repo = DBManager.get_facilities_repository(db)
        try:
            deleted = await repo.delete(facility_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Удобство не найдено")
    
    # Инвалидируем кэш удобств
    await FastAPICache.clear(namespace="facilities")
    
    return MessageResponse(status="OK")

