"""
Вспомогательные функции для работы с метриками.
"""

import os

from src.config import settings


def should_collect_metrics() -> bool:
    """
    Проверить, нужно ли собирать метрики.

    Метрики собираются если:
    - Не в тестовом режиме (DB_NAME != "test"), ИЛИ
    - В тестовом режиме, но включены через ENABLE_METRICS_IN_TESTS=true

    Примечание: Проверяем os.environ напрямую, чтобы поддержать динамическое
    изменение переменной окружения в тестах без перезагрузки настроек.

    Returns:
        True если нужно собирать метрики, False иначе
    """
    if settings.DB_NAME != "test":
        return True

    # В тестовом режиме проверяем переменную окружения напрямую
    # (чтобы поддержать динамическое изменение в тестах)
    enable_metrics = os.getenv("ENABLE_METRICS_IN_TESTS", "false").lower()
    return enable_metrics in ("true", "1", "yes")
