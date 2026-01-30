from fastapi import HTTPException
from typing import Optional, TypeVar, Generic, Callable, Awaitable
from src.utils.db_manager import DBManager
from fastapi_cache import FastAPICache

T = TypeVar('T')


async def get_or_404(
    repo_get_method: Callable[[int], Awaitable[Optional[T]]],
    entity_id: int,
    entity_name: str
) -> T:
    """
    Получить сущность по ID или выбросить 404 если не найдена.
    
    Args:
        repo_get_method: Метод репозитория для получения сущности (например, repo.get_by_id)
        entity_id: ID сущности
        entity_name: Название сущности для сообщения об ошибке (например, "Отель", "Пользователь")
        
    Returns:
        Найденная сущность
        
    Raises:
        HTTPException: 404 если сущность не найдена
    """
    entity = await repo_get_method(entity_id)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"{entity_name} не найден" if entity_name.endswith(("а", "я", "ь")) else f"{entity_name} не найдено"
        )
    return entity


async def invalidate_cache(namespace: str) -> None:
    """
    Инвалидировать кэш для указанного namespace.
    
    Args:
        namespace: Namespace кэша для очистки (например, "hotels", "rooms", "cities")
    """
    await FastAPICache.clear(namespace=namespace)


async def handle_delete_operation(
    delete_func: Callable[[int], Awaitable[bool]],
    entity_id: int,
    entity_name: str
) -> None:
    """
    Обработать операцию удаления с единообразной обработкой ошибок.
    
    Args:
        delete_func: Функция удаления из репозитория (например, repo.delete)
        entity_id: ID сущности для удаления
        entity_name: Название сущности для сообщения об ошибке
        
    Raises:
        HTTPException: 400 если произошла ошибка ValueError
        HTTPException: 404 если сущность не найдена
    """
    try:
        deleted = await delete_func(entity_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not deleted:
        entity_name_formatted = entity_name
        if entity_name.endswith(("а", "я", "ь")):
            entity_name_formatted = f"{entity_name} не найдена"
        elif entity_name.endswith("о"):
            entity_name_formatted = f"{entity_name} не найдено"
        else:
            entity_name_formatted = f"{entity_name} не найден"
        raise HTTPException(status_code=404, detail=entity_name_formatted)


async def validate_city_by_name(
    db,
    city_name: str
) -> int:
    """
    Валидировать существование города по названию (без учета регистра) и вернуть его ID.
    
    Args:
        db: Сессия базы данных
        city_name: Название города
        
    Returns:
        int: ID города
        
    Raises:
        HTTPException: 404 если город не найден
    """
    from src.utils.db_manager import DBManager
    cities_repo = DBManager.get_cities_repository(db)
    city_orm = await cities_repo.get_by_name_case_insensitive(city_name)
    if city_orm is None:
        raise HTTPException(
            status_code=404,
            detail=f"Город '{city_name}' не найден"
        )
    return city_orm.id

