import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Response
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
    summary="Health check",
    description="Проверка состояния приложения, подключения к БД, Redis, Celery и дискового пространства",
    tags=["Система"],
)
async def health_check(db: DBDep) -> dict:
    """
    Проверка состояния приложения.

    Returns:
        Словарь со статусом приложения, БД, Redis, Celery и дискового пространства
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

    return status


@router.get(
    "/ready",
    summary="Readiness check",
    description="Проверка готовности приложения к обработке запросов",
    tags=["Система"],
)
async def readiness_check(db: DBDep) -> dict:
    """
    Проверка готовности приложения.

    Returns:
        Словарь со статусом готовности
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"ready": True, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Приложение не готово: {e}", exc_info=True)
        return {"ready": False, "timestamp": datetime.now().isoformat(), "error": str(e)}


@router.get(
    "/live",
    summary="Liveness check",
    description="Проверка жизнеспособности приложения",
    tags=["Система"],
)
async def liveness_check() -> dict:
    """
    Проверка жизнеспособности приложения.

    Returns:
        Словарь со статусом жизнеспособности
    """
    return {"alive": True, "timestamp": datetime.now().isoformat()}


@router.get(
    "/metrics",
    summary="Prometheus metrics",
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
