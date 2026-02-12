import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.api.dependencies import DBDep
from src.metrics.setup import get_metrics
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Минимальный процент свободного места на диске (по умолчанию 10%)
MIN_DISK_FREE_PERCENT = 10


def check_disk_space(path: Path = Path("/")) -> dict:
    """
    Проверить свободное место на диске.

    Args:
        path: Путь для проверки дискового пространства (по умолчанию корень файловой системы)

    Returns:
        Словарь со статусом дискового пространства
    """
    try:
        total, used, free = shutil.disk_usage(path)
        free_percent = (free / total) * 100

        return {
            "status": "ok" if free_percent >= MIN_DISK_FREE_PERCENT else "warning",
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "free_percent": round(free_percent, 2),
            "min_free_percent": MIN_DISK_FREE_PERCENT,
        }
    except Exception as e:
        logger.error(f"Ошибка проверки дискового пространства: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }


def check_celery_workers() -> dict:
    """
    Проверить доступность Celery workers.

    Returns:
        Словарь со статусом Celery workers
    """
    try:
        from src.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect()
        if inspector is None:
            return {
                "status": "no_workers",
                "message": "Celery broker доступен, но активные workers не найдены",
            }

        # Проверяем доступность workers через ping
        ping_result = inspector.ping()
        if ping_result:
            active_workers = list(ping_result.keys())
            return {
                "status": "ok",
                "workers_count": len(active_workers),
                "workers": active_workers,
            }
        else:
            return {
                "status": "no_workers",
                "message": "Celery broker доступен, но workers не отвечают",
            }
    except Exception as e:
        logger.error(f"Ошибка проверки Celery workers: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }


@router.get(
    "/health",
    summary="Простая проверка состояния",
    description=(
        "Простая проверка состояния приложения. "
        "Возвращает базовый статус без детальной диагностики. "
        "Для детальной проверки используйте /health/detailed."
    ),
    tags=["Система"],
    response_class=JSONResponse,
)
async def health_check():
    """
    Простая проверка состояния приложения.

    Returns:
        Словарь с базовым статусом {"status": "ok"}
    """
    return JSONResponse(content={"status": "ok"}, media_type="application/json")


@router.get(
    "/health/detailed",
    summary="Детальная проверка состояния приложения",
    description=(
        "Подробная проверка состояния приложения и всех зависимостей. "
        "Проверяет подключения к БД, Redis, Celery и дисковое пространство. "
        "Возвращает детальный статус каждого компонента. "
        "Используется для мониторинга и диагностики состояния системы. "
        "В отличие от /ready, проверяет все компоненты, а не только критичные для работы. "
        "Для простой проверки используйте /health."
    ),
    tags=["Система"],
    response_class=JSONResponse,
)
async def health_check_detailed(db: DBDep):
    """
    Подробная проверка состояния приложения и всех зависимостей.

    Health check проверяет все компоненты системы (БД, Redis, Celery, диск) и возвращает
    детальный статус каждого. Используется для мониторинга и диагностики.
    В отличие от readiness check, health check проверяет все компоненты, включая некритичные.

    Returns:
        Словарь с детальным статусом всех компонентов системы
    """
    status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "database": "unknown",
        "redis": "unknown",
        "celery": "unknown",
        "disk": "unknown",
    }

    # Проверка БД
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        status["database"] = "connected"
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}", exc_info=True)
        status["database"] = "disconnected"
        status["status"] = "degraded"

    # Проверка Redis
    try:
        from src import redis_manager

        is_connected = await redis_manager.check_connection()
        if is_connected:
            status["redis"] = "connected"
        else:
            status["redis"] = "disconnected"
            status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Ошибка подключения к Redis: {e}", exc_info=True)
        status["redis"] = "disconnected"
        status["status"] = "degraded"

    # Проверка Celery workers
    celery_status = check_celery_workers()
    status["celery"] = celery_status
    if celery_status.get("status") == "error":
        status["status"] = "degraded"
    elif celery_status.get("status") == "no_workers":
        # Отсутствие workers - это warning, но не критично для работы API
        if status["status"] == "ok":
            status["status"] = "degraded"

    # Проверка дискового пространства
    disk_status = check_disk_space()
    status["disk"] = disk_status
    if disk_status.get("status") == "error":
        status["status"] = "degraded"
    elif disk_status.get("status") == "warning":
        # Мало места на диске - это warning, но не критично
        if status["status"] == "ok":
            status["status"] = "degraded"

    # Если БД недоступна, приложение полностью не работает
    if status["database"] == "disconnected":
        status["status"] = "down"

    return JSONResponse(content=status, media_type="application/json")


@router.get(
    "/live",
    summary="Проверка жизнеспособности",
    description=(
        "Проверка жизнеспособности приложения. "
        "Проверяет, что процесс приложения работает и отвечает на запросы. "
        "Используется Kubernetes для определения, нужно ли перезапустить под. "
        "Не проверяет подключения к внешним сервисам (база данных, Redis, Celery) - "
        "только факт того, что сам процесс приложения запущен и отвечает."
    ),
    tags=["Система"],
    response_class=JSONResponse,
)
async def liveness_check() -> dict:
    """
    Проверка жизнеспособности приложения.

    Liveness probe проверяет, что процесс приложения работает и не завис.
    В отличие от readiness probe, liveness не проверяет подключения к внешним сервисам
    (база данных, Redis, Celery) - только факт работы самого процесса.
    Используется Kubernetes для принятия решения о перезапуске пода при сбое процесса.

    Returns:
        Словарь со статусом жизнеспособности (alive: bool, timestamp: str)
    """
    return {"alive": True, "timestamp": datetime.now().isoformat()}


@router.get(
    "/ready",
    summary="Проверка готовности",
    description=(
        "Проверка готовности приложения к обработке запросов. "
        "Проверяет только критичные зависимости (база данных). "
        "Используется Kubernetes для определения, когда под готов принимать трафик. "
        "Возвращает простой ответ ready: true/false. "
        "В отличие от /health, проверяет только критичные компоненты для работы API."
    ),
    tags=["Система"],
    response_class=JSONResponse,
)
async def readiness_check(db: DBDep) -> dict:
    """
    Проверка готовности приложения к обработке запросов.

    Readiness probe проверяет только критичные зависимости (БД) для работы API.
    Используется Kubernetes для управления трафиком - если ready=false, Kubernetes
    не будет направлять запросы на под.
    В отличие от health check, проверяет только критичные компоненты, а не все.

    Returns:
        Словарь со статусом готовности (ready: bool, timestamp: str, error?: str)
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"ready": True, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Приложение не готово: {e}", exc_info=True)
        return {"ready": False, "timestamp": datetime.now().isoformat(), "error": str(e)}


@router.get(
    "/metrics",
    summary="Метрики Prometheus",
    description="Эндпоинт для сбора метрик Prometheus. Возвращает все метрики в формате Prometheus.",
    tags=["Система"],
)
async def metrics() -> Response:
    """
    Получить метрики Prometheus.

    Returns:
        Response с метриками в формате Prometheus (text/plain)
    """
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain; version=0.0.4; charset=utf-8")
