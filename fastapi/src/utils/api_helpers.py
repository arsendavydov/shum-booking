from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import HTTPException
from fastapi_cache import FastAPICache

T = TypeVar("T")


async def get_or_404(repo_get_method: Callable[[int], Awaitable[T | None]], entity_id: int, entity_name: str) -> T:
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
            detail=f"{entity_name} не найден" if entity_name.endswith(("а", "я", "ь")) else f"{entity_name} не найдено",
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
    delete_func: Callable[[int], Awaitable[bool]], entity_id: int, entity_name: str
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


async def validate_entity_exists(
    find_method: Callable[..., Awaitable[Any | None]], entity_name: str, *args: Any, **kwargs: Any
) -> Any:
    """
    Валидировать существование сущности и вернуть её.

    Универсальная функция для проверки существования любой сущности
    по любому критерию (ID, название, и т.д.).

    Args:
        find_method: Метод репозитория для поиска сущности (например, repo.get_by_id, repo.get_by_name_case_insensitive)
        entity_name: Название сущности для сообщения об ошибке (например, "Город", "Страна")
        *args: Позиционные аргументы для метода поиска
        **kwargs: Именованные аргументы для метода поиска

    Returns:
        Найденная сущность (ORM объект или схема)

    Raises:
        HTTPException: 404 если сущность не найдена
    """
    entity = await find_method(*args, **kwargs)
    if entity is None:
        # Формируем сообщение об ошибке
        if args:
            search_value = args[0]
        elif kwargs:
            search_value = list(kwargs.values())[0]
        else:
            search_value = ""

        raise HTTPException(
            status_code=404,
            detail=f"{entity_name} '{search_value}' не найден" if search_value else f"{entity_name} не найден",
        )
    return entity


def handle_validation_error(error: ValueError) -> HTTPException:
    """
    Преобразовать ValueError из репозитория в HTTPException с корректным статус-кодом.

    Анализирует текст ошибки и определяет соответствующий HTTP статус-код:
    - 404 для ошибок "не найден", "не найдена", "не найдено"
    - 409 для ошибок "уже существует"
    - 400 для остальных ошибок

    Args:
        error: ValueError из репозитория

    Returns:
        HTTPException с соответствующим статус-кодом
    """
    error_message = str(error)
    error_lower = error_message.lower()

    # Сначала проверяем на ошибки "уже существует" (409)
    # Это должно быть первым, чтобы не перехватывать сообщения типа "Город 'X' уже существует"
    if "уже существует" in error_lower:
        return HTTPException(status_code=409, detail=error_message)

    # Затем проверяем на ошибки "не найден" (404)
    if any(phrase in error_lower for phrase in ["не найден", "не найдена", "не найдено"]):
        return HTTPException(status_code=404, detail=error_message)

    # Остальные ошибки - 400
    return HTTPException(status_code=400, detail=error_message)
