from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Ленивая инициализация engine - создается только при первом использовании
_engine = None
_async_session_maker_instance = None

def _get_engine():
    """Получить engine, создавая его при первом вызове."""
    global _engine
    if _engine is None:
        DB_URL = f"postgresql+asyncpg://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        _engine = create_async_engine(DB_URL)
    return _engine

def _get_async_session_maker():
    """Получить async_session_maker, создавая его при первом вызове."""
    global _async_session_maker_instance
    if _async_session_maker_instance is None:
        _async_session_maker_instance = async_sessionmaker(bind=_get_engine(), expire_on_commit=False)
    return _async_session_maker_instance



async def check_connection():
    """Проверка подключения к базе данных."""
    async with _get_engine().begin() as conn:
        res = await conn.execute(text("SELECT version()"))
        result = res.fetchone()
        if result:
            logger.debug(f"PostgreSQL version: {result[0]}")
        return result


async def close_engine():
    """Закрытие подключения к базе данных."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None