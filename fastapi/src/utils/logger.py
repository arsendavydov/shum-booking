"""
Модуль для настройки логирования приложения.

Создает единую систему логирования для FastAPI и Celery.
Логи пишутся в файл и в консоль.
"""

import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Путь к папке с логами (fastapi/logs/)
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Путь к файлу логов
LOG_FILE = LOGS_DIR / "app.log"

# Формат логов
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = None) -> logging.Logger:
    """
    Настроить систему логирования для приложения.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  Если не указан, берется из settings.LOG_LEVEL или по умолчанию INFO.
    
    Returns:
        Настроенный root logger
    """
    # Получаем уровень логирования
    if log_level is None:
        # Пытаемся получить из settings, если доступен, иначе из переменных окружения
        try:
            from src.config import settings
            log_level = getattr(settings, 'LOG_LEVEL', 'INFO')
        except Exception:
            log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Создаем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Очищаем существующие handlers
    root_logger.handlers.clear()
    
    # Форматтер
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    # Handler для файла (с ротацией)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 МБ
        backupCount=5,  # Храним 5 файлов
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Handler для консоли (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Настраиваем логирование для сторонних библиотек
    # Uvicorn - используем propagate=True, чтобы логи шли через root logger
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(level)
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = True  # Пропагируем в root logger
    
    # Uvicorn access (HTTP запросы)
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.setLevel(level)
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.propagate = True  # Пропагируем в root logger
    
    # FastAPI - используем propagate=True
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.setLevel(level)
    fastapi_logger.handlers.clear()
    fastapi_logger.propagate = True  # Пропагируем в root logger
    
    # SQLAlchemy (опционально, можно отключить для уменьшения объема логов)
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.WARNING)  # Только WARNING и выше для SQLAlchemy
    sqlalchemy_logger.handlers.clear()
    sqlalchemy_logger.addHandler(file_handler)
    sqlalchemy_logger.addHandler(console_handler)
    sqlalchemy_logger.propagate = False
    
    # Celery - используем propagate=True
    celery_logger = logging.getLogger("celery")
    celery_logger.setLevel(level)
    celery_logger.handlers.clear()
    celery_logger.propagate = True  # Пропагируем в root logger
    
    # Celery task
    celery_task_logger = logging.getLogger("celery.task")
    celery_task_logger.setLevel(level)
    celery_task_logger.handlers.clear()
    celery_task_logger.propagate = True  # Пропагируем в root logger
    
    # Celery worker
    celery_worker_logger = logging.getLogger("celery.worker")
    celery_worker_logger.setLevel(level)
    celery_worker_logger.handlers.clear()
    celery_worker_logger.propagate = True  # Пропагируем в root logger
    
    # Alembic - используем propagate=True
    alembic_logger = logging.getLogger("alembic")
    alembic_logger.setLevel(level)
    alembic_logger.handlers.clear()
    alembic_logger.propagate = True  # Пропагируем в root logger
    
    # Alembic runtime (миграции)
    alembic_runtime_logger = logging.getLogger("alembic.runtime.migration")
    alembic_runtime_logger.setLevel(level)
    alembic_runtime_logger.handlers.clear()
    alembic_runtime_logger.propagate = True  # Пропагируем в root logger
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Получить logger для модуля.
    
    Args:
        name: Имя модуля (обычно __name__)
    
    Returns:
        Logger для указанного модуля
    """
    return logging.getLogger(name)

