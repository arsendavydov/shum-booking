"""
Пакет с тестами.

Важно:
- Не делаем импорт из `tests.conftest` на уровне модуля, чтобы при запуске
  unit-тестов (tests/unit_tests) не требовался `.test.env` и переменная TEST_PASSWORD.
- API-тесты и другие тесты, которым нужны BASE_URL/TEST_*,
  импортируют их напрямую из `tests.conftest`.
"""

__all__: list[str] = []
