from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Добавляем корень проекта в sys.path для импорта модулей
# Определяем путь так же, как PROJECT_ROOT в config.py (fastapi/src/config.py -> fastapi/)
# Используем локальную переменную, так как импорт config требует добавления пути в sys.path
# После добавления пути можно использовать PROJECT_ROOT из src.config в других местах
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Импорт Base из base.py (не из db.py, чтобы избежать создания async engine)
from src.base import Base
from src.models.countries import CountriesOrm
from src.models.cities import CitiesOrm
from src.models.hotels import HotelsOrm
from src.models.rooms import RoomsOrm
from src.models.users import UsersOrm
from src.models.bookings import BookingsOrm
from src.models.facilities import FacilitiesOrm
from src.models.images import ImagesOrm
from src.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Настройка URL базы данных для Alembic (синхронный драйвер)
# Alembic использует синхронный psycopg2, а не asyncpg
# Если запускаем локально, используем localhost вместо postgres (имя Docker сервиса)
db_host = settings.DB_HOST
if db_host == "postgres":
    # Проверяем, доступен ли хост postgres (Docker), если нет - используем localhost
    import socket
    try:
        socket.gethostbyname("postgres")
    except socket.gaierror:
        db_host = "localhost"

db_url = f"postgresql://{settings.DB_USERNAME}:{settings.DB_PASSWORD}@{db_host}:{settings.DB_PORT}/{settings.DB_NAME}"
config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Переопределяем логирование Alembic, чтобы использовать нашу систему логирования
# Это нужно, чтобы логи Alembic попадали в наш файл логов
try:
    from src.utils.logger import setup_logging
    import logging
    
    # Настраиваем логирование (если еще не настроено)
    setup_logging()
    
    # Убеждаемся, что логгеры Alembic используют нашу систему
    # Очищаем handlers, созданные fileConfig, и устанавливаем propagate=True
    alembic_logger = logging.getLogger("alembic")
    alembic_logger.handlers.clear()
    alembic_logger.propagate = True
    
    alembic_runtime_logger = logging.getLogger("alembic.runtime.migration")
    alembic_runtime_logger.handlers.clear()
    alembic_runtime_logger.propagate = True
    
    # Также настраиваем все подлоггеры alembic
    for logger_name in logging.Logger.manager.loggerDict:
        if logger_name.startswith("alembic"):
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.propagate = True
except Exception:
    # Если не удалось импортировать setup_logging, используем стандартное логирование Alembic
    pass

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata 

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
