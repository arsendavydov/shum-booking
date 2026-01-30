import pytest
import httpx
import time
from tests.api_tests import TEST_PASSWORD, TEST_EXAMPLE_EMAIL_DOMAIN


@pytest.mark.auth
class TestAuth:
    """Эндпоинты аутентификации"""
    
    def test_register_user_minimal(self, client, test_prefix, created_user_ids):
        """Минимальная регистрация"""
        unique_email = f"{test_prefix}_test_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": TEST_PASSWORD
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == unique_email
        assert data["hashed_password"] is not None
        assert data["first_name"] is None
        assert data["last_name"] is None
        created_user_ids.append(data["id"])
    
    def test_register_user_full(self, client, test_prefix, created_user_ids):
        """Полная регистрация"""
        unique_email = f"{test_prefix}_fulluser_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": TEST_PASSWORD,
                "first_name": "Иван",
                "last_name": "Иванов",
                "telegram_id": 123456789,
                "pachca_id": 987654321
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == unique_email
        assert data["hashed_password"] is not None
        assert data["first_name"] == "Иван"
        assert data["last_name"] == "Иванов"
        assert data["telegram_id"] == 123456789
        assert data["pachca_id"] == 987654321
        created_user_ids.append(data["id"])
    
    def test_register_user_duplicate_email(self, client, test_prefix, created_user_ids):
        """Регистрация с дублирующимся email"""
        unique_email = f"{test_prefix}_duplicate_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        create_response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": TEST_PASSWORD
            }
        )
        assert create_response.status_code == 201
        created_data = create_response.json()
        created_user_ids.append(created_data["id"])
        
        response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": TEST_PASSWORD
            }
        )
        assert response.status_code == 409
        assert "уже существует" in response.json()["detail"]
    
    def test_register_user_invalid_email(self, client):
        """Регистрация с невалидным email"""
        response = client.post(
            "/auth/register",
            json={
                "email": "invalid-email",
                "password": TEST_PASSWORD
            }
        )
        assert response.status_code == 422
    
    def test_register_user_short_password(self, client):
        """Регистрация с коротким паролем"""
        response = client.post(
            "/auth/register",
            json={
                "email": f"shortpass@{TEST_EXAMPLE_EMAIL_DOMAIN}",
                "password": "short"
            }
        )
        assert response.status_code == 422
    
    def test_register_user_missing_email(self, client):
        """Регистрация без email"""
        response = client.post(
            "/auth/register",
            json={
                "password": TEST_PASSWORD
            }
        )
        assert response.status_code == 422
    
    def test_register_user_missing_password(self, client):
        """Регистрация без password"""
        response = client.post(
            "/auth/register",
            json={
                "email": f"nopass@{TEST_EXAMPLE_EMAIL_DOMAIN}"
            }
        )
        assert response.status_code == 422
    
    def test_login_user_success(self, client, test_prefix, created_user_ids):
        """Вход пользователя"""
        unique_email = f"{test_prefix}_login_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        password = TEST_PASSWORD
        
        register_response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": password
            }
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])
        
        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email,
                "password": password
            }
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert token_data["token_type"] == "bearer"
        assert len(token_data["access_token"]) > 0
        
        cookies = login_response.cookies
        assert "access_token" in cookies
        assert cookies["access_token"] == token_data["access_token"]
    
    def test_login_user_wrong_email(self, client):
        """Вход с неверным email"""
        response = client.post(
            "/auth/login",
            json={
                "email": f"nonexistent@{TEST_EXAMPLE_EMAIL_DOMAIN}",
                "password": TEST_PASSWORD
            }
        )
        assert response.status_code == 401
        assert "Пользователь с таким email не найден" in response.json()["detail"]
    
    def test_login_user_wrong_password(self, client, test_prefix, created_user_ids):
        """Вход с неверным паролем"""
        unique_email = f"{test_prefix}_wrongpass_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        
        register_response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": TEST_PASSWORD
            }
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])
        
        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email,
                "password": "wrongpass123"  # Намеренно неправильный пароль для теста
            }
        )
        assert login_response.status_code == 401
        assert "Неверный пароль" in login_response.json()["detail"]
    
    def test_login_user_invalid_email(self, client):
        """Вход с невалидным email"""
        response = client.post(
            "/auth/login",
            json={
                "email": "invalid-email",
                "password": TEST_PASSWORD
            }
        )
        assert response.status_code == 422
    
    def test_login_user_missing_email(self, client):
        """Вход без email"""
        response = client.post(
            "/auth/login",
            json={
                "password": TEST_PASSWORD
            }
        )
        assert response.status_code == 422
    
    def test_login_user_missing_password(self, client):
        """Вход без password"""
        response = client.post(
            "/auth/login",
            json={
                "email": f"user@{TEST_EXAMPLE_EMAIL_DOMAIN}"
            }
        )
        assert response.status_code == 422
    
    def test_get_current_user_success_with_cookie(self, client, test_prefix, created_user_ids):
        """Получение текущего пользователя через cookie"""
        unique_email = f"{test_prefix}_me_cookie_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        password = TEST_PASSWORD
        
        register_response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": password,
                "first_name": "Тест",
                "last_name": "Пользователь"
            }
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])
        
        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email,
                "password": password
            }
        )
        assert login_response.status_code == 200
        
        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        me_data = me_response.json()
        
        assert me_data["id"] == user_data["id"]
        assert me_data["email"] == unique_email
        assert me_data["first_name"] == "Тест"
        assert me_data["last_name"] == "Пользователь"
    
    def test_get_current_user_success_with_header(self, client, test_prefix, created_user_ids):
        """Получение текущего пользователя через header"""
        unique_email = f"{test_prefix}_me_header_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        password = TEST_PASSWORD
        
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        
        register_response = test_client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": password
            }
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])
        
        login_response = test_client.post(
            "/auth/login",
            json={
                "email": unique_email,
                "password": password
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        clean_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        me_response = clean_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        
        assert me_data["id"] == user_data["id"]
        assert me_data["email"] == unique_email
        
        test_client.close()
        clean_client.close()
    
    def test_get_current_user_no_token(self, client):
        """Получение текущего пользователя без токена"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        response = test_client.get("/auth/me")
        assert response.status_code == 401
        assert "Токен доступа не предоставлен" in response.json()["detail"]
        test_client.close()
    
    def test_get_current_user_invalid_token(self, client):
        """Получение текущего пользователя с невалидным токеном"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        response = test_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401
        assert "Токен невалиден или истек" in response.json()["detail"]
        test_client.close()
    
    def test_get_current_user_malformed_token(self, client):
        """Получение текущего пользователя с неправильным форматом токена"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        response = test_client.get(
            "/auth/me",
            headers={"Authorization": "InvalidFormat token123"}
        )
        assert response.status_code == 401
        assert "Токен доступа не предоставлен" in response.json()["detail"]
        test_client.close()
    
    def test_logout_user_success(self, client, test_prefix, created_user_ids):
        """Вход выхода пользователя"""
        unique_email = f"{test_prefix}_logout_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        password = TEST_PASSWORD
        
        register_response = client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": password
            }
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])
        
        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email,
                "password": password
            }
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.cookies
        
        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 200
        assert logout_response.json() == {"status": "OK"}
    
    def test_logout_user_no_auth(self, client):
        """Выход без авторизации"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        response = test_client.post("/auth/logout")
        assert response.status_code == 401
        assert "Токен доступа не предоставлен" in response.json()["detail"]
        test_client.close()

