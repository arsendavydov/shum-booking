import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

root_logger = logging.getLogger()


class HTTPLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования HTTP запросов (только для основного приложения)."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start_time = time.time()
        response = await call_next(request)
        _process_time = time.time() - start_time  # Время обработки (можно использовать для метрик)

        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_string = str(request.url.query)
        if query_string:
            path = f"{path}?{query_string}"
        status_code = response.status_code
        protocol = request.scope.get("http_version", "HTTP/1.1")
        if not protocol.startswith("HTTP/"):
            protocol = f"HTTP/{protocol}"

        log_message = f'{client_host} - "{method} {path} {protocol}" {status_code}'
        root_logger.info(log_message)

        return response

