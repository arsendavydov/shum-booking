import os
import time
from pathlib import Path

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis as AsyncRedis

from src import redis_manager
from src.config import settings
from src.db import check_connection, close_engine
from src.utils.logger import get_logger
from src.utils.migrations import apply_migrations_for_current_db, setup_test_database

logger = get_logger(__name__)


async def startup_handler():
    """Обработчик запуска приложения."""
    setup_test_database()
    await apply_migrations_for_current_db()

    logger.info("Проверка подключения к базе данных...")
    try:
        await check_connection()
        logger.info("Подключение к базе данных успешно установлено!")
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}", exc_info=True)
        raise

    logger.info("Проверка подключения к Redis...")
    try:
        await redis_manager.connect()
        is_connected = await redis_manager.check_connection()
        if is_connected:
            logger.info("Подключение к Redis успешно установлено!")
        else:
            raise Exception("Redis не отвечает на ping")
    except Exception as e:
        logger.error(f"Ошибка подключения к Redis: {e}", exc_info=True)
        raise

    redis_cache_client = AsyncRedis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    FastAPICache.init(RedisBackend(redis_cache_client), prefix="fastapi-cache")
    logger.info("FastAPI Cache инициализирован с Redis!")

    cleanup_temp_files()


async def shutdown_handler():
    """Обработчик остановки приложения."""
    logger.info("Закрытие соединений с базой данных...")
    try:
        await close_engine()
        logger.info("Соединение с базой данных закрыто")
    except Exception as e:
        logger.warning(f"Ошибка при закрытии соединения с базой данных: {e}", exc_info=True)

    logger.info("Закрытие соединений с Redis...")
    try:
        await redis_manager.close()
        logger.info("Соединение с Redis закрыто")
    except Exception as e:
        logger.warning(f"Ошибка при закрытии соединения с Redis: {e}", exc_info=True)


def cleanup_temp_files() -> None:
    """Очистить старые временные файлы (старше 1 часа)."""
    temp_dir = Path(__file__).resolve().parent.parent.parent.parent / "static" / "temp"
    if not temp_dir.exists():
        return

    current_time = time.time()
    cleaned_count = 0
    for file_path in temp_dir.iterdir():
        if file_path.is_file():
            try:
                file_age = current_time - file_path.stat().st_mtime
                if file_age > 3600:
                    os.remove(file_path)
                    cleaned_count += 1
            except Exception:
                pass

    if cleaned_count > 0:
        logger.info(f"Очищено {cleaned_count} старых временных файлов при старте")
