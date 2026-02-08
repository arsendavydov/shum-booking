# Экспорт переменных из conftest для удобного импорта в тестах
from tests.conftest import BASE_URL, TEST_EXAMPLE_EMAIL_DOMAIN, TEST_PASSWORD

__all__ = ["BASE_URL", "TEST_EXAMPLE_EMAIL_DOMAIN", "TEST_PASSWORD"]

