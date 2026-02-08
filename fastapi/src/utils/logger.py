"""
Модуль для настройки логирования приложения.

Создает единую систему логирования для FastAPI и Celery.
Логи пишутся в файл и в консоль.
"""

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# Путь к папке с логами (fastapi/logs/)
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Формат логов для текстового вывода
TEXT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Константы для handlers
MAX_BYTES = 10 * 1024 * 1024  # 10 МБ
BACKUP_COUNT = 5


def _use_json_logs() -> bool:
    """
    Определить, включено ли JSON-логирование.

    Управляется переменной окружения LOG_FORMAT_JSON:
    - "1", "true", "yes" (регистр не важен) -> JSON-логирование включено
    - любое другое значение или отсутствие переменной -> обычный текстовый формат
    """
    value = os.getenv("LOG_FORMAT_JSON", "false").lower()
    return value in {"1", "true", "yes"}


class JsonFormatter(logging.Formatter):
    """Форматтер, который сериализует записи лога в JSON."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        # Базовые поля
        log_record: dict[str, Any] = {
            "timestamp": self.formatTime(record, DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Полезные стандартные поля (без path с полным путем, чтобы не раздувать лог)
        log_record.update(
            {
                "module": record.module,
                "funcName": record.funcName,
                "line": record.lineno,
            }
        )

        # Добавляем все дополнительные поля, которые могли быть переданы через extra
        # Исключаем стандартные атрибуты LogRecord
        standard_keys = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }

        for key, value in record.__dict__.items():
            if key not in standard_keys and key not in log_record:
                try:
                    json.dumps(value)  # проверяем, что значение сериализуемо
                    log_record[key] = value
                except TypeError:
                    # Несериализуемые объекты в JSON не добавляем
                    log_record[key] = repr(value)

        return json.dumps(log_record, ensure_ascii=False)


def _get_log_level() -> str:
    """Получить уровень логирования из settings или переменных окружения."""
    try:
        from src.config import settings

        return getattr(settings, "LOG_LEVEL", "INFO")
    except Exception:
        return os.getenv("LOG_LEVEL", "INFO")


def _create_handlers(log_file: Path, level: int) -> tuple[logging.FileHandler, logging.StreamHandler[Any]]:
    """Создать file и console handlers с общим форматтером."""
    # Выбираем форматтер в зависимости от настройки LOG_FORMAT_JSON
    if _use_json_logs():
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(TEXT_LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8", delay=False
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    return file_handler, console_handler


def setup_logging(log_level: str | None = None, log_file_name: str = "app.log") -> None:
    """
    Настроить систему логирования для приложения.

    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  Если не указан, берется из settings.LOG_LEVEL или по умолчанию INFO.
        log_file_name: Имя файла для логов (по умолчанию "app.log")
    """
    # Получаем уровень логирования
    if log_level is None:
        log_level = _get_log_level()

    level = getattr(logging, log_level.upper(), logging.INFO)
    log_file = LOGS_DIR / log_file_name

    # Создаем handlers
    file_handler, console_handler = _create_handlers(log_file, level)

    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Настраиваем логгеры для сторонних библиотек
    # Логгеры, которые должны пропагировать в root logger
    propagate_loggers = [
        "uvicorn",
        "uvicorn.error",
        "fastapi",
        "celery",
        "celery.task",
        "celery.worker",
        "alembic",
        "alembic.runtime.migration",
        "src.middleware.http_logging",  # HTTP‑middleware всегда пропагирует в root
    ]

    for logger_name in propagate_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.handlers.clear()
        logger.propagate = True

    # SQLAlchemy - только WARNING и выше, не пропагирует
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.WARNING)
    sqlalchemy_logger.handlers.clear()
    sqlalchemy_logger.addHandler(file_handler)
    sqlalchemy_logger.addHandler(console_handler)
    sqlalchemy_logger.propagate = False

    # python-multipart (загрузка файлов) - глушим DEBUG-спам, оставляем только WARNING+
    multipart_logger = logging.getLogger("python_multipart.multipart")
    multipart_logger.setLevel(logging.WARNING)
    multipart_logger.handlers.clear()
    multipart_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Получить logger для модуля.

    Args:
        name: Имя модуля (обычно __name__)

    Returns:
        Logger для указанного модуля
    """
    return logging.getLogger(name)
