"""
Модуль для настройки и инициализации метрик Prometheus.
"""

from datetime import UTC, datetime

from fastapi import FastAPI
from prometheus_client import REGISTRY, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from src.metrics.collectors import (
    app_info,
    app_uptime_seconds,
)
from src.metrics.helpers import should_collect_metrics

# Время запуска приложения для расчета uptime
_app_start_time = datetime.now(UTC)


def setup_prometheus_instrumentator(app: FastAPI) -> None:
    """
    Настроить prometheus-fastapi-instrumentator для автоматического сбора HTTP метрик.

    Args:
        app: Экземпляр FastAPI приложения
    """
    if not should_collect_metrics():
        return

    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/ready", "/live"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    instrumentator.instrument(app).expose(app)


def update_system_metrics() -> None:
    """Обновить системные метрики (uptime).

    Примечание: process_resident_memory_bytes и process_cpu_seconds_total
    обновляются автоматически prometheus-fastapi-instrumentator.
    """
    if not should_collect_metrics():
        return

    try:
        uptime = (datetime.now(UTC) - _app_start_time).total_seconds()
        app_uptime_seconds.set(uptime)
        app_info.labels(version="1.0.0").set(1)
    except Exception:
        pass


def get_metrics() -> str:
    """
    Получить все метрики в формате Prometheus.

    Returns:
        Строка с метриками в формате Prometheus
    """
    update_system_metrics()
    return generate_latest(REGISTRY).decode("utf-8")
