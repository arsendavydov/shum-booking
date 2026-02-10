"""
E2E (End-to-End) тесты для проверки полных пользовательских сценариев.

E2E тесты проверяют полный поток от начала до конца, проходя через все слои приложения.
Они медленнее, чем unit и API тесты, но дают уверенность, что система работает как единое целое.

Запуск:
    pytest tests/e2e_tests/ -v
    pytest -m e2e -v

Настройка BASE_URL:
    По умолчанию: http://localhost:8001
    Можно изменить через переменную окружения E2E_BASE_URL:
    E2E_BASE_URL=https://async-black.ru/apps/shum-booking pytest tests/e2e_tests/ -v
"""

__all__: list[str] = []

