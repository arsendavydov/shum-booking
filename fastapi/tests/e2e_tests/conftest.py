"""
Конфигурация для E2E тестов.

BASE_URL можно настроить через переменную окружения E2E_BASE_URL.
По умолчанию используется localhost для локального тестирования.
"""
import os
import time
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv

# BASE_URL для E2E тестов - можно изменить через переменную окружения
# По умолчанию: localhost (для локального тестирования)
# Для тестирования production: E2E_BASE_URL=https://async-black.ru/apps/shum-booking
E2E_BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8001")

# Задержка между вызовами API (в секундах)
E2E_REQUEST_DELAY = float(os.getenv("E2E_REQUEST_DELAY", "0.1"))

# Загружаем переменные окружения из .test.env (если есть)
env_test_path = Path(__file__).resolve().parent.parent.parent / ".test.env"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)

TEST_PASSWORD = os.getenv("TEST_PASSWORD", "test_password_123")
TEST_EXAMPLE_EMAIL_DOMAIN = os.getenv("TEST_EXAMPLE_EMAIL_DOMAIN", "shum-booking.com")


@pytest.fixture(scope="session")
def e2e_base_url():
    """BASE_URL для E2E тестов"""
    return E2E_BASE_URL


@pytest.fixture(scope="session")
def e2e_client(e2e_base_url):
    """HTTP клиент для E2E тестов"""
    with httpx.Client(base_url=e2e_base_url, timeout=30.0, follow_redirects=True) as client:
        yield client


@pytest.fixture(scope="function")
def delay():
    """Задержка между вызовами API (0.1 секунда по умолчанию)"""
    return E2E_REQUEST_DELAY


def wait_between_requests(delay: float):
    """Вспомогательная функция для задержки между запросами"""
    if delay > 0:
        time.sleep(delay)


@pytest.fixture(scope="function")
def test_user_email():
    """Генерирует уникальный email для тестового пользователя"""
    return f"e2e_test_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"


@pytest.fixture(scope="function", autouse=True)
def print_e2e_info(e2e_base_url):
    """Выводит информацию о настройках E2E тестов"""
    print(f"\n🔍 E2E тесты настроены:")
    print(f"   BASE_URL: {e2e_base_url}")
    print(f"   Задержка между запросами: {E2E_REQUEST_DELAY}s")
    yield

