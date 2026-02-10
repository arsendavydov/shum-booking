# Инициализация пакета src
"""
Пакет src - основной код приложения.

Важно: RedisManager импортируется лениво, чтобы не требовать модуль redis
при простом импорте модулей (например, для unit-тестов).
"""
from typing import Any


def get_redis_manager():
    """Ленивая инициализация RedisManager."""
    from src.connectors.redis_connector import RedisManager

    if not hasattr(get_redis_manager, "_instance"):
        get_redis_manager._instance = RedisManager()
    return get_redis_manager._instance


# Экспортируем redis_manager как свойство для обратной совместимости
# При первом обращении будет создан экземпляр
class _RedisManagerProxy:
    """Прокси для ленивой инициализации RedisManager."""

    def __getattr__(self, name: str) -> Any:
        manager = get_redis_manager()
        return getattr(manager, name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        manager = get_redis_manager()
        return manager(*args, **kwargs)


redis_manager = _RedisManagerProxy()
