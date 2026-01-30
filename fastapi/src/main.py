from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
import os
import time
from pathlib import Path
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from src.api import (
    hotels_router,
    auth_router,
    users_router,
    rooms_router,
    bookings_router,
    facilities_router,
    images_router,
    countries_router,
    cities_router
)
from src.config import settings
from src.db import check_connection, close_engine
from src import redis_manager
from src.utils.logger import setup_logging, get_logger

# Инициализируем логирование ДО создания приложения, чтобы все логи попадали в файл
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan события для FastAPI - выполняется при старте и остановке приложения."""
    
    # Создание и применение миграций к тестовой БД при запуске в режиме local
    if settings.DB_NAME == "booking":
        logger.info("Проверка и создание тестовой БД...")
        try:
            import psycopg2
            # Подключаемся к postgres БД для создания test БД
            conn = psycopg2.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USERNAME,
                password=settings.DB_PASSWORD,
                database="postgres"  # Подключаемся к системной БД
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Проверяем, существует ли БД test
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'test'")
            exists = cursor.fetchone()
            
            if not exists:
                logger.info("Создание тестовой БД...")
                cursor.execute('CREATE DATABASE test')
                logger.info("Тестовая БД создана!")
            else:
                logger.info("Тестовая БД уже существует")
            
            cursor.close()
            conn.close()
            
            # Применяем миграции к тестовой БД
            logger.info("Применение миграций к тестовой БД...")
            from alembic.config import Config
            from alembic import command
            
            alembic_ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
            if alembic_ini_path.exists():
                alembic_cfg = Config(str(alembic_ini_path))
                test_db_url = f"postgresql://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/test"
                alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
                command.upgrade(alembic_cfg, "head")
                logger.info("Миграции применены к тестовой БД!")
            else:
                logger.warning("Файл alembic.ini не найден, миграции не применены")
        except Exception as e:
            logger.error(f"Ошибка при работе с тестовой БД: {e}", exc_info=True)
    
    # Применяем миграции для тестовой БД, если DB_NAME=test
    # Примечание: Очистка БД выполняется в conftest.py через drop_all/create_all,
    # поэтому здесь только применяем миграции для создания структуры таблиц
    if settings.DB_NAME == "test":
        logger.info("Применение миграций к тестовой БД...")
        try:
            from alembic.config import Config
            from alembic import command
            
            # Путь к alembic.ini (находится в fastapi/alembic.ini)
            alembic_ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
            
            if alembic_ini_path.exists():
                alembic_cfg = Config(str(alembic_ini_path))
                # Обновляем URL БД для тестовой БД
                db_url = f"postgresql://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
                alembic_cfg.set_main_option("sqlalchemy.url", db_url)
                
                # Пытаемся применить миграции
                try:
                    command.upgrade(alembic_cfg, "head")
                    logger.info("Миграции применены к тестовой БД!")
                except Exception as migration_error:
                    # Если миграции уже применены (таблицы существуют), помечаем их как примененные
                    error_str = str(migration_error)
                    if "already exists" in error_str or "DuplicateTable" in error_str:
                        logger.warning("Таблицы уже существуют, помечаем миграции как примененные...")
                        command.stamp(alembic_cfg, "head")
                        logger.info("Миграции помечены как примененные!")
                    else:
                        raise migration_error
            else:
                logger.warning("Файл alembic.ini не найден, миграции не применены")
        except Exception as e:
            logger.error(f"Ошибка при применении миграций: {e}", exc_info=True)
    
    # Startup: проверка подключения к БД и Redis
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
    
    # Инициализация FastAPI Cache с Redis
    from redis.asyncio import Redis as AsyncRedis
    redis_cache_client = AsyncRedis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )
    FastAPICache.init(RedisBackend(redis_cache_client), prefix="fastapi-cache")
    logger.info("FastAPI Cache инициализирован с Redis!")
    
    # Очистка старых временных файлов при старте
    temp_dir = Path(__file__).resolve().parent.parent / "static" / "temp"
    if temp_dir.exists():
        current_time = time.time()
        cleaned_count = 0
        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                try:
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > 3600:  # Старше 1 часа
                        os.remove(file_path)
                        cleaned_count += 1
                except Exception:
                    pass
        if cleaned_count > 0:
            logger.info(f"Очищено {cleaned_count} старых временных файлов при старте")
    
    yield  # Приложение работает
    
    # Shutdown: закрытие соединений
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


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router, prefix="/auth", tags=["Аутентификация"])
app.include_router(users_router, prefix="/users", tags=["Пользователи"])
app.include_router(hotels_router, prefix="/hotels", tags=["Отели"])
app.include_router(rooms_router, prefix="/hotels/{hotel_id}/rooms", tags=["Номера"])
app.include_router(bookings_router, prefix="/bookings", tags=["Бронирования"])
app.include_router(facilities_router, prefix="/facilities", tags=["Удобства"])
app.include_router(images_router, prefix="/images", tags=["Изображения отелей"])
app.include_router(countries_router, prefix="/countries", tags=["Страны"])
app.include_router(cities_router, prefix="/cities", tags=["Города"])

if __name__ == "__main__":
    uvicorn.run(app="src.main:app", host="127.0.0.1", port=8000, reload=True)
