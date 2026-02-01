import time

import httpx
import pytest

from tests.api_tests import TEST_EXAMPLE_EMAIL_DOMAIN, TEST_PASSWORD


@pytest.mark.auth
class TestAuth:
    """Эндпоинты аутентификации"""

    def test_register_user_minimal(self, client, test_prefix, created_user_ids):
        """Минимальная регистрация"""
        unique_email = f"{test_prefix}_test_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        response = client.post("/auth/register", json={"email": unique_email, "password": TEST_PASSWORD})
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == unique_email
        assert "hashed_password" not in data
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
                "pachca_id": 987654321,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == unique_email
        assert "hashed_password" not in data
        assert data["first_name"] == "Иван"
        assert data["last_name"] == "Иванов"
        assert data["telegram_id"] == 123456789
        assert data["pachca_id"] == 987654321
        created_user_ids.append(data["id"])

    def test_register_user_duplicate_email(self, client, test_prefix, created_user_ids):
        """Регистрация с дублирующимся email"""
        unique_email = f"{test_prefix}_duplicate_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        create_response = client.post("/auth/register", json={"email": unique_email, "password": TEST_PASSWORD})
        assert create_response.status_code == 201
        created_data = create_response.json()
        created_user_ids.append(created_data["id"])

        response = client.post("/auth/register", json={"email": unique_email, "password": TEST_PASSWORD})
        assert response.status_code == 409
        assert "уже существует" in response.json()["detail"]

    @pytest.mark.parametrize(
        "invalid_data,expected_status",
        [
            ({"email": "invalid-email", "password": TEST_PASSWORD}, 422),
            ({"email": f"shortpass@{TEST_EXAMPLE_EMAIL_DOMAIN}", "password": "short"}, 422),
        ],
    )
    def test_register_user_invalid_data(self, client, invalid_data, expected_status):
        """Регистрация с невалидными данными"""
        response = client.post("/auth/register", json=invalid_data)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "invalid_email,description",
        [
            ("", "пустой email"),
            ("notanemail", "email без @"),
            ("@nodomain.com", "email без локальной части"),
            ("nodomain@", "email без домена"),
            ("spaces in@email.com", "email с пробелами"),
            ("email@domain", "email без TLD"),
            ("email@.com", "email с пустым доменом"),
            ("email@@domain.com", "email с двойным @"),
            ("email@domain..com", "email с двойной точкой в домене"),
            ("email@domain.com.", "email с точкой в конце"),
            (".email@domain.com", "email с точкой в начале"),
            ("email@" + "d" * 250 + ".com", "очень длинный домен"),
        ],
    )
    def test_register_user_invalid_email_formats(self, client, invalid_email, description):
        """Регистрация с различными невалидными форматами email"""
        response = client.post("/auth/register", json={"email": invalid_email, "password": TEST_PASSWORD})
        assert response.status_code == 422, f"Ожидался 422 для {description}: {invalid_email}"

    @pytest.mark.parametrize(
        "invalid_password,description",
        [
            ("", "пустой пароль"),
            ("short", "слишком короткий пароль (меньше 8 символов)"),
            ("1234567", "пароль из 7 цифр"),
            ("abcdefg", "пароль из 7 букв"),
        ],
    )
    def test_register_user_invalid_passwords(self, client, test_prefix, invalid_password, description):
        """Регистрация с различными невалидными паролями"""
        unique_email = f"{test_prefix}_invalidpass_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        response = client.post("/auth/register", json={"email": unique_email, "password": invalid_password})
        assert response.status_code == 422, f"Ожидался 422 для {description}"

    @pytest.mark.parametrize(
        "invalid_data,expected_status",
        [
            ({"email": "", "password": TEST_PASSWORD}, 422),
            ({"email": f"test@{TEST_EXAMPLE_EMAIL_DOMAIN}", "password": ""}, 422),
            ({"email": "", "password": ""}, 422),
            (None, 422),
            ({}, 422),
        ],
    )
    def test_register_user_empty_values(self, client, invalid_data, expected_status):
        """Регистрация с пустыми значениями"""
        if invalid_data is None:
            response = client.post("/auth/register", json=None)
        else:
            response = client.post("/auth/register", json=invalid_data)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "missing_field,json_data",
        [
            ("email", {"password": TEST_PASSWORD}),
            ("password", {"email": f"nopass@{TEST_EXAMPLE_EMAIL_DOMAIN}"}),
        ],
    )
    def test_register_user_missing_field(self, client, missing_field, json_data):
        """Регистрация без обязательного поля"""
        response = client.post("/auth/register", json=json_data)
        assert response.status_code == 422

    def test_login_user_success(self, client, test_prefix, created_user_ids):
        """Вход пользователя"""
        unique_email = f"{test_prefix}_login_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        password = TEST_PASSWORD

        register_response = client.post("/auth/register", json={"email": unique_email, "password": password})
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])

        login_response = client.post("/auth/login", json={"email": unique_email, "password": password})
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
            "/auth/login", json={"email": f"nonexistent@{TEST_EXAMPLE_EMAIL_DOMAIN}", "password": TEST_PASSWORD}
        )
        assert response.status_code == 401
        assert "Пользователь с таким email не найден" in response.json()["detail"]

    def test_login_user_wrong_password(self, client, test_prefix, created_user_ids):
        """Вход с неверным паролем"""
        unique_email = f"{test_prefix}_wrongpass_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"

        register_response = client.post("/auth/register", json={"email": unique_email, "password": TEST_PASSWORD})
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])

        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email,
                "password": "wrongpass123",  # Намеренно неправильный пароль для теста
            },
        )
        assert login_response.status_code == 401
        assert "Неверный пароль" in login_response.json()["detail"]

    @pytest.mark.parametrize(
        "invalid_email,description",
        [
            ("", "пустой email"),
            ("notanemail", "email без @"),
            ("@nodomain.com", "email без локальной части"),
            ("nodomain@", "email без домена"),
            ("spaces in@email.com", "email с пробелами"),
            ("email@domain", "email без TLD"),
            ("email@.com", "email с пустым доменом"),
            ("email@@domain.com", "email с двойным @"),
            ("email@domain..com", "email с двойной точкой в домене"),
            ("email@domain.com.", "email с точкой в конце"),
            (".email@domain.com", "email с точкой в начале"),
            ("email@" + "d" * 250 + ".com", "очень длинный домен"),
        ],
    )
    def test_login_user_invalid_email_formats(self, client, invalid_email, description):
        """Вход с различными невалидными форматами email"""
        response = client.post("/auth/login", json={"email": invalid_email, "password": TEST_PASSWORD})
        assert response.status_code == 422, f"Ожидался 422 для {description}: {invalid_email}"

    @pytest.mark.parametrize(
        "invalid_password,description",
        [
            ("", "пустой пароль"),
            ("short", "слишком короткий пароль"),
            ("1234567", "пароль из 7 цифр"),
            ("abcdefg", "пароль из 7 букв"),
        ],
    )
    def test_login_user_invalid_passwords(self, client, test_prefix, created_user_ids, invalid_password, description):
        """Вход с различными невалидными паролями"""
        unique_email = f"{test_prefix}_login_invalidpass_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"

        register_response = client.post("/auth/register", json={"email": unique_email, "password": TEST_PASSWORD})
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])

        login_response = client.post("/auth/login", json={"email": unique_email, "password": invalid_password})
        assert login_response.status_code in [401, 422], f"Ожидался 401 или 422 для {description}"

    @pytest.mark.parametrize(
        "invalid_data,expected_status",
        [
            ({"email": "", "password": TEST_PASSWORD}, 422),
            ({"email": f"test@{TEST_EXAMPLE_EMAIL_DOMAIN}", "password": ""}, 422),
            ({"email": "", "password": ""}, 422),
            (None, 422),
            ({}, 422),
        ],
    )
    def test_login_user_empty_values(self, client, invalid_data, expected_status):
        """Вход с пустыми значениями"""
        if invalid_data is None:
            response = client.post("/auth/login", json=None)
        else:
            response = client.post("/auth/login", json=invalid_data)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "missing_field,json_data",
        [
            ("email", {"password": TEST_PASSWORD}),
            ("password", {"email": f"user@{TEST_EXAMPLE_EMAIL_DOMAIN}"}),
        ],
    )
    def test_login_user_missing_field(self, client, missing_field, json_data):
        """Вход без обязательного поля"""
        response = client.post("/auth/login", json=json_data)
        assert response.status_code == 422

    def test_get_current_user_success_with_cookie(self, client, test_prefix, created_user_ids):
        """Получение текущего пользователя через cookie"""
        unique_email = f"{test_prefix}_me_cookie_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        password = TEST_PASSWORD

        register_response = client.post(
            "/auth/register",
            json={"email": unique_email, "password": password, "first_name": "Тест", "last_name": "Пользователь"},
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])

        login_response = client.post("/auth/login", json={"email": unique_email, "password": password})
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

        register_response = test_client.post("/auth/register", json={"email": unique_email, "password": password})
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])

        login_response = test_client.post("/auth/login", json={"email": unique_email, "password": password})
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        clean_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        me_response = clean_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
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
        response = test_client.get("/auth/me", headers={"Authorization": "Bearer invalid_token_12345"})
        assert response.status_code == 401
        assert "Токен невалиден или истек" in response.json()["detail"]
        test_client.close()

    def test_get_current_user_malformed_token(self, client):
        """Получение текущего пользователя с неправильным форматом токена"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        response = test_client.get("/auth/me", headers={"Authorization": "InvalidFormat token123"})
        assert response.status_code == 401
        assert "Токен доступа не предоставлен" in response.json()["detail"]
        test_client.close()

    @pytest.mark.parametrize(
        "invalid_token,description,expect_httpx_error",
        [
            ("", "пустой токен", False),
            ("not_a_token", "токен без Bearer", False),
            ("Bearer ", "токен с пустым значением после Bearer", True),
            ("Bearer not.jwt.token", "невалидный JWT формат", False),
            ("Bearer a.b", "неполный JWT (2 части вместо 3)", False),
            ("Bearer a.b.c.d", "JWT с лишними частями", False),
            ("Bearer " + "a" * 1000, "очень длинный токен", False),
            ("Bearer " + "a" * 10, "очень короткий токен", False),
            ("Bearer токен", "токен с кириллицей", True),
            ("Bearer token with spaces", "токен с пробелами", False),
            ("Bearer\ttoken", "токен с табуляцией", False),
            ("Bearer\ntoken", "токен с переносом строки", True),
            ("Basic token123", "неправильный тип авторизации", False),
            ("Token token123", "неправильный формат", False),
        ],
    )
    def test_get_current_user_invalid_token_formats(self, client, invalid_token, description, expect_httpx_error):
        """Получение текущего пользователя с различными невалидными форматами токена"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)

        if expect_httpx_error:
            with pytest.raises((httpx.LocalProtocolError, UnicodeEncodeError)):
                test_client.get("/auth/me", headers={"Authorization": invalid_token})
        else:
            response = test_client.get("/auth/me", headers={"Authorization": invalid_token})
            assert response.status_code == 401, f"Ожидался 401 для {description}"

        test_client.close()

    def test_logout_user_success(self, client, test_prefix, created_user_ids):
        """Выход пользователя"""
        unique_email = f"{test_prefix}_logout_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        password = TEST_PASSWORD

        register_response = client.post("/auth/register", json={"email": unique_email, "password": password})
        assert register_response.status_code == 201
        user_data = register_response.json()
        created_user_ids.append(user_data["id"])

        login_response = client.post("/auth/login", json={"email": unique_email, "password": password})
        assert login_response.status_code == 200
        assert "access_token" in login_response.cookies
        token_before_logout = login_response.cookies.get("access_token")
        assert token_before_logout is not None

        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 200
        assert logout_response.json() == {"status": "OK"}

        token_after_logout = logout_response.cookies.get("access_token")
        assert token_after_logout is None or token_after_logout == "", (
            "Токен должен быть удален из cookies после logout"
        )

        me_response = client.get("/auth/me")
        assert me_response.status_code == 401, "После logout токен не должен работать"

    def test_logout_user_no_auth(self, client):
        """Выход без авторизации"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        response = test_client.post("/auth/logout")
        assert response.status_code == 401
        assert "Токен доступа не предоставлен" in response.json()["detail"]
        test_client.close()

    @pytest.mark.parametrize(
        "invalid_token,description,expect_httpx_error",
        [
            ("", "пустой токен", False),
            ("not_a_token", "токен без Bearer", False),
            ("Bearer ", "токен с пустым значением после Bearer", True),
            ("Bearer not.jwt.token", "невалидный JWT формат", False),
            ("Bearer a.b", "неполный JWT (2 части вместо 3)", False),
            ("Bearer a.b.c.d", "JWT с лишними частями", False),
            ("Bearer " + "a" * 1000, "очень длинный токен", False),
            ("Bearer " + "a" * 10, "очень короткий токен", False),
            ("Bearer токен", "токен с кириллицей", True),
            ("Bearer token with spaces", "токен с пробелами", False),
            ("Basic token123", "неправильный тип авторизации", False),
            ("Token token123", "неправильный формат", False),
        ],
    )
    def test_logout_user_invalid_token_formats(self, client, invalid_token, description, expect_httpx_error):
        """Выход с различными невалидными форматами токена"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)

        if expect_httpx_error:
            with pytest.raises((httpx.LocalProtocolError, UnicodeEncodeError)):
                test_client.post("/auth/logout", headers={"Authorization": invalid_token})
        else:
            response = test_client.post("/auth/logout", headers={"Authorization": invalid_token})
            assert response.status_code == 401, f"Ожидался 401 для {description}"

        test_client.close()
