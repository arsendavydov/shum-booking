import time

import pytest

from tests.api_tests import BASE_URL


@pytest.mark.auth
class TestRefreshTokens:
    """Тесты для refresh токенов."""

    def test_login_returns_refresh_token(self, client):
        """Проверить, что /auth/login возвращает refresh токен."""
        timestamp = int(time.time() * 1000)
        email = f"test_refresh_{timestamp}@example.com"
        password = "testpass123"

        # Регистрация пользователя
        register_response = client.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "password": password},
        )
        assert register_response.status_code == 201

        # Вход
        login_response = client.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200
        data = login_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert len(data["refresh_token"]) > 0

    def test_refresh_token_updates_access_token(self, client):
        """Проверить, что /auth/refresh обновляет access токен."""
        timestamp = int(time.time() * 1000)
        email = f"test_refresh2_{timestamp}@example.com"
        password = "testpass123"

        # Регистрация и вход
        client.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password})
        login_response = client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        assert login_response.status_code == 200
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]

        # Обновление токена
        refresh_response = client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        # Refresh токен должен быть новым
        assert refresh_data["refresh_token"] != refresh_token
        # Access токен может быть таким же, если создан в ту же секунду, но должен быть валидным
        assert len(refresh_data["access_token"]) > 0

    def test_refresh_token_invalid_token(self, client):
        """Проверить, что невалидный refresh токен возвращает 401."""
        response = client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": "invalid_token_12345"},
        )
        assert response.status_code == 401
        assert "невалидный" in response.json()["detail"].lower() or "истекший" in response.json()["detail"].lower()

    def test_refresh_token_revoked_after_use(self, client):
        """Проверить, что refresh токен нельзя использовать дважды."""
        timestamp = int(time.time() * 1000)
        email = f"test_refresh3_{timestamp}@example.com"
        password = "testpass123"

        # Регистрация и вход
        client.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password})
        login_response = client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Первое использование refresh токена
        refresh_response1 = client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response1.status_code == 200

        # Второе использование того же refresh токена должно вернуть 401
        refresh_response2 = client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response2.status_code == 401

    def test_logout_revokes_all_refresh_tokens(self, client):
        """Проверить, что /auth/logout отзывает все refresh токены пользователя."""
        timestamp = int(time.time() * 1000)
        email = f"test_refresh4_{timestamp}@example.com"
        password = "testpass123"

        # Регистрация и вход
        client.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password})
        login_response = client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        assert login_response.status_code == 200
        refresh_token1 = login_response.json()["refresh_token"]
        access_token = login_response.json()["access_token"]

        # Второй вход (создаем второй refresh токен)
        login_response2 = client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        assert login_response2.status_code == 200
        refresh_token2 = login_response2.json()["refresh_token"]

        # Выход
        logout_response = client.post(
            f"{BASE_URL}/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_response.status_code == 200

        # Оба refresh токена должны быть отозваны
        refresh_response1 = client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token1},
        )
        assert refresh_response1.status_code == 401

        refresh_response2 = client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token2},
        )
        assert refresh_response2.status_code == 401

    def test_refresh_token_with_new_access_token_works(self, client):
        """Проверить, что новый access токен после refresh работает."""
        timestamp = int(time.time() * 1000)
        email = f"test_refresh5_{timestamp}@example.com"
        password = "testpass123"

        # Регистрация и вход
        client.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password})
        login_response = client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Обновление токена
        refresh_response = client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]

        # Проверяем, что новый access токен работает
        me_response = client.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == email
