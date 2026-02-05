"""
Middleware для rate limiting (ограничение количества запросов).

Защищает API от brute-force атак и DDoS.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings
from src.metrics.collectors import rate_limit_exceeded_total, rate_limit_requests_total

# Создаем экземпляр limiter
# Используем get_remote_address для определения IP клиента
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler_with_metrics(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Обработчик ошибок rate limiting с метриками.

    Args:
        request: FastAPI Request объект
        exc: Исключение RateLimitExceeded

    Returns:
        Response с ошибкой 429
    """
    endpoint = request.url.path
    rate_limit_exceeded_total.labels(endpoint=endpoint).inc()
    # _rate_limit_exceeded_handler возвращает Response (не awaitable)
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[return-value]


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Настроить rate limiting для приложения.

    Args:
        app: Экземпляр FastAPI приложения
    """
    if not settings.RATE_LIMIT_ENABLED:
        return

    # Подключаем limiter к приложению
    app.state.limiter = limiter

    # Регистрируем обработчик ошибок rate limiting с метриками
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler_with_metrics)

    # Добавляем middleware для сбора метрик rate limiting
    @app.middleware("http")
    async def rate_limit_metrics_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        endpoint = request.url.path
        if settings.DB_NAME != "test":
            rate_limit_requests_total.labels(endpoint=endpoint).inc()
        response = await call_next(request)
        return response


# Экспортируем декоратор для использования в роутерах
# В slowapi декоратор работает с Request объектом через app.state.limiter
def rate_limit(limit_value: str):
    """
    Декоратор для ограничения количества запросов к эндпоинту.

    Args:
        limit_value: Строка с лимитом, например "5/minute" или "60/hour"

    Returns:
        Декоратор для применения к эндпоинту
    """
    # Если rate limiting отключен, возвращаем пустой декоратор
    # Проверяем также, не в тестовом режиме ли мы (если DB_NAME == "test" и RATE_LIMIT_ENABLED_IN_TESTS не установлен)
    import os

    is_test_mode = settings.DB_NAME == "test"
    rate_limit_enabled_in_tests = os.getenv("RATE_LIMIT_ENABLED_IN_TESTS", "false").lower() == "true"

    if not settings.RATE_LIMIT_ENABLED or (is_test_mode and not rate_limit_enabled_in_tests):

        def noop_decorator(func: Callable) -> Callable:
            return func

        return noop_decorator

    # Возвращаем оригинальный декоратор
    # Метрики будут собираться в обработчике ошибок и через middleware
    return limiter.limit(limit_value)
