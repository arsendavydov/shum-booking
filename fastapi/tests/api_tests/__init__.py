# Экспорт переменных из conftest для удобного импорта в тестах
from tests.conftest import TEST_EXAMPLE_EMAIL_DOMAIN, TEST_PASSWORD

__all__ = ["TEST_EXAMPLE_EMAIL_DOMAIN", "TEST_PASSWORD"]
