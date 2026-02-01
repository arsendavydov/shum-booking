# Экспорт общих переменных и фикстур из conftest для удобного импорта
from tests.conftest import BASE_URL, TEST_EXAMPLE_EMAIL_DOMAIN, TEST_PASSWORD, TEST_PREFIX

__all__ = ["BASE_URL", "TEST_EXAMPLE_EMAIL_DOMAIN", "TEST_PASSWORD", "TEST_PREFIX"]
