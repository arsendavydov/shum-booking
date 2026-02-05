import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from src.metrics.collectors import api_errors_total, api_request_duration_seconds, api_requests_total
from src.metrics.helpers import should_collect_metrics
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HTTPLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования HTTP‑запросов."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Логирование всех HTTP‑запросов в формате access‑log."""

        start_time = time.time()
        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_string = str(request.url.query)
        if query_string:
            path = f"{path}?{query_string}"
        protocol = request.scope.get("http_version", "HTTP/1.1")
        if not protocol.startswith("HTTP/"):
            protocol = f"HTTP/{protocol}"

        status_code = 500  # По умолчанию, если произойдет ошибка
        response: Response | None = None
        endpoint = request.url.path
        error_type = None

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            # Логируем запрос даже если произошла ошибка
            error_type = type(exc).__name__
            logger.error(f"Ошибка при обработке запроса {method} {path}", exc_info=True)
            if should_collect_metrics():
                api_errors_total.labels(endpoint=endpoint, error_type=error_type).inc()
            raise exc
        finally:
            process_time = time.time() - start_time
            log_message = f'{client_host} - "{method} {path} {protocol}" {status_code} {process_time:.3f}s'
            # Логируем и через модульный логгер, и через root‑логгер,
            # чтобы гарантированно попасть и в app.log, и в stdout контейнера.
            logger.info(log_message)
            logging.getLogger().info(log_message)

            # Собираем метрики
            if should_collect_metrics():
                api_requests_total.labels(endpoint=endpoint, method=method, status=status_code).inc()
                api_request_duration_seconds.labels(endpoint=endpoint, method=method).observe(process_time)

        return response
