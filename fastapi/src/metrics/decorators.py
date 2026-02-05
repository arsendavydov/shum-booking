"""
Декораторы для сбора метрик.
"""

import functools
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from src.config import settings
from src.metrics.collectors import (
    cache_hits_total,
    cache_misses_total,
    cache_operation_duration_seconds,
    cache_operations_total,
    db_queries_total,
    db_query_duration_seconds,
)

T = TypeVar("T")


def track_db_query(operation: str):
    """
    Декоратор для отслеживания запросов к базе данных.

    Args:
        operation: Тип операции (SELECT, INSERT, UPDATE, DELETE)

    Returns:
        Декоратор для применения к функции
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if settings.DB_NAME == "test":
                return await func(*args, **kwargs)

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                db_queries_total.labels(operation=operation).inc()
                return result
            finally:
                duration = time.time() - start_time
                db_query_duration_seconds.labels(operation=operation).observe(duration)

        return wrapper

    return decorator


def track_cache_operation(operation: str, namespace: str = "default"):
    """
    Декоратор для отслеживания операций с кэшем.

    Args:
        operation: Тип операции (get, set, delete)
        namespace: Пространство имен кэша

    Returns:
        Декоратор для применения к функции
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if settings.DB_NAME == "test":
                return await func(*args, **kwargs)

            start_time = time.time()
            cache_operations_total.labels(operation=operation, namespace=namespace).inc()

            try:
                result = await func(*args, **kwargs)

                if operation == "get":
                    if result is None:
                        cache_misses_total.labels(namespace=namespace).inc()
                    else:
                        cache_hits_total.labels(namespace=namespace).inc()

                return result
            finally:
                duration = time.time() - start_time
                cache_operation_duration_seconds.labels(operation=operation, namespace=namespace).observe(duration)

        return wrapper

    return decorator
