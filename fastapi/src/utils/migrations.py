from pathlib import Path

from alembic import command
from alembic.config import Config

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def setup_test_database():
    """Создать тестовую БД и применить к ней миграции (вызывается при запуске в режиме local)."""
    if settings.DB_NAME != "booking":
        return

    logger.info("Проверка и создание тестовой БД...")
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USERNAME,
            password=settings.DB_PASSWORD,
            database="postgres",
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'test'")
        exists = cursor.fetchone()

        if not exists:
            logger.info("Создание тестовой БД...")
            cursor.execute("CREATE DATABASE test")
            logger.info("Тестовая БД создана!")
        else:
            logger.info("Тестовая БД уже существует")

        cursor.close()
        conn.close()

        apply_migrations_to_test_db()
    except Exception as e:
        logger.error(f"Ошибка при работе с тестовой БД: {e}", exc_info=True)


def apply_migrations_to_test_db():
    """Применить миграции к тестовой БД."""
    logger.info("Применение миграций к тестовой БД...")
    try:
        alembic_ini_path = Path(__file__).resolve().parent.parent.parent.parent / "alembic.ini"
        if not alembic_ini_path.exists():
            logger.warning("Файл alembic.ini не найден, миграции не применены")
            return

        alembic_cfg = Config(str(alembic_ini_path))
        test_db_url = (
            f"postgresql://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/test"
        )
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Миграции применены к тестовой БД!")
    except Exception as e:
        logger.error(f"Ошибка при применении миграций к тестовой БД: {e}", exc_info=True)


async def apply_migrations_for_current_db():
    """Применить миграции для текущей БД (используется при DB_NAME=test)."""
    if settings.DB_NAME != "test":
        return

    logger.info("Применение миграций к тестовой БД...")
    try:
        alembic_ini_path = Path(__file__).resolve().parent.parent.parent.parent / "alembic.ini"

        if not alembic_ini_path.exists():
            logger.warning("Файл alembic.ini не найден, миграции не применены")
            return

        alembic_cfg = Config(str(alembic_ini_path))
        db_url = f"postgresql://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        try:
            command.upgrade(alembic_cfg, "head")
            logger.info("Миграции применены к тестовой БД!")
        except Exception as migration_error:
            error_str = str(migration_error)
            if "already exists" in error_str or "DuplicateTable" in error_str:
                logger.warning("Таблицы уже существуют, помечаем миграции как примененные...")
                command.stamp(alembic_cfg, "head")
                logger.info("Миграции помечены как примененные!")
            else:
                raise migration_error
    except Exception as e:
        logger.error(f"Ошибка при применении миграций: {e}", exc_info=True)
