import json
import logging
import os
from pathlib import Path

import pytest

from src.utils.logger import LOGS_DIR, get_logger, setup_logging


pytestmark = pytest.mark.unit


def _read_last_log_line(log_file: Path) -> str:
    with log_file.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    assert lines, "Файл логов пуст"
    return lines[-1].strip()


def test_text_logging_default_format(tmp_path, monkeypatch):
    """По умолчанию используется текстовый формат логов."""
    # Явно выключаем JSON формат
    monkeypatch.delenv("LOG_FORMAT_JSON", raising=False)

    log_file_name = "test_text_logging.log"
    log_file = LOGS_DIR / log_file_name
    if log_file.exists():
        log_file.unlink()

    setup_logging(log_level="INFO", log_file_name=log_file_name)
    logger = get_logger(__name__)
    logger.info("Text log message")

    line = _read_last_log_line(log_file)
    # Текстовый формат должен содержать уровень и имя логгера в строке
    assert "[INFO]" in line
    assert __name__ in line
    assert "Text log message" in line


def test_json_logging_enabled(monkeypatch):
    """При LOG_FORMAT_JSON=true логи пишутся в формате JSON."""
    monkeypatch.setenv("LOG_FORMAT_JSON", "true")

    log_file_name = "test_json_logging.log"
    log_file = LOGS_DIR / log_file_name
    if log_file.exists():
        log_file.unlink()

    setup_logging(log_level="INFO", log_file_name=log_file_name)
    logger = get_logger("test_json_logger")
    logger.info("Json log message", extra={"request_id": "req-123"})

    line = _read_last_log_line(log_file)

    data = json.loads(line)
    assert data["level"] == "INFO"
    assert data["logger"] == "test_json_logger"
    assert data["message"] == "Json log message"
    assert data["request_id"] == "req-123"
    assert "timestamp" in data


