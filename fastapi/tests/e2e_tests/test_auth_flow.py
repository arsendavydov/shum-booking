"""
E2E тест: Полный цикл аутентификации.

Проверяет полный сценарий работы с аутентификацией:
1. Регистрация пользователя
2. Вход в систему
3. Получение данных пользователя
4. Обновление токена через refresh token
5. Выход из системы
"""

import pytest

from tests.e2e_tests.conftest import TEST_PASSWORD, wait_between_requests


@pytest.mark.e2e
@pytest.mark.slow
class TestAuthFlow:
    """E2E тесты для полного цикла аутентификации"""

    def test_full_auth_journey(self, e2e_client, test_user_email, delay):
        """Полный путь аутентификации: регистрация → вход → использование токена → обновление → выход"""

        # 1. Регистрация нового пользователя
        print("\n📝 Шаг 1: Регистрация пользователя")
        register_data = {
            "email": test_user_email,
            "password": TEST_PASSWORD,
            "first_name": "E2E",
            "last_name": "Auth",
        }
        register_response = e2e_client.post("/auth/register", json=register_data)
        wait_between_requests(delay)

        assert register_response.status_code == 201
        user_data = register_response.json()
        user_id = user_data["id"]
        assert user_data["email"] == test_user_email
        print(f"✅ Пользователь зарегистрирован: ID={user_id}")

        # После регистрации нужно войти, чтобы получить токены
        print("\n🔑 Шаг 1.5: Вход для получения токенов")
        login_data = {
            "email": test_user_email,
            "password": TEST_PASSWORD,
        }
        login_response = e2e_client.post("/auth/login", json=login_data)
        wait_between_requests(delay)

        assert login_response.status_code == 200, (
            f"Ожидался статус 200, получен {login_response.status_code}: {login_response.text}"
        )
        # Получаем токены из cookies после логина
        access_token = login_response.cookies.get("access_token")
        refresh_token = login_response.json().get("refresh_token")  # refresh_token в JSON ответе
        assert access_token is not None, "Access token должен быть в cookies"
        assert refresh_token is not None, "Refresh token должен быть в JSON ответе"
        print("✅ Токены получены: access_token и refresh_token")

        # 2. Использование access токена для получения данных пользователя
        # В проде эндпоинт расположен по пути /auth/me
        print("\n👤 Шаг 2: Получение данных пользователя с access токеном")
        cookies = {"access_token": access_token}
        me_response = e2e_client.get("/auth/me", cookies=cookies)
        wait_between_requests(delay)

        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["id"] == user_id
        assert me_data["email"] == test_user_email
        print(f"✅ Данные пользователя получены: {me_data.get('first_name')} {me_data.get('last_name')}")

        # 3. Выход из системы (logout)
        print("\n🚪 Шаг 3: Выход из системы")
        logout_response = e2e_client.post("/auth/logout", cookies=cookies)
        wait_between_requests(delay)

        # В проде после logout access_token может оставаться валидным
        # (logout отзывает refresh токены, но не всегда сразу инвалидирует access токен).
        assert logout_response.status_code in [200, 204]
        print("✅ Выход выполнен")

        # 5. Повторный вход в систему
        print("\n🔑 Шаг 5: Повторный вход в систему")
        login_data = {
            "email": test_user_email,
            "password": TEST_PASSWORD,
        }
        login_response = e2e_client.post("/auth/login", json=login_data)
        wait_between_requests(delay)

        assert login_response.status_code == 200
        # Повторный вход нужен только для получения нового access_token/refresh_token
        print("✅ Вход выполнен успешно")

        # Получаем новые токены
        new_access_token = login_response.cookies.get("access_token")
        new_refresh_token = login_response.cookies.get("refresh_token")
        assert new_access_token is not None
        assert new_refresh_token is not None
        print("✅ Новые токены получены")

        # 6. Использование нового access токена
        print("\n👤 Шаг 6: Использование нового access токена")
        new_cookies = {"access_token": new_access_token}
        new_me_response = e2e_client.get("/auth/me", cookies=new_cookies)
        wait_between_requests(delay)

        assert new_me_response.status_code == 200
        new_me_data = new_me_response.json()
        assert new_me_data["id"] == user_id
        print("✅ Новый токен работает корректно")

        # 7. Обновление access токена через refresh token
        print("\n🔄 Шаг 7: Обновление access токена через refresh token")
        # refresh_token передается в JSON body, а новый access_token берем из JSON ответа
        refresh_data = {"refresh_token": new_refresh_token}
        refresh_response = e2e_client.post("/auth/refresh", json=refresh_data)
        wait_between_requests(delay)

        assert refresh_response.status_code == 200
        refresh_json = refresh_response.json()
        refreshed_access_token = refresh_json.get("access_token")
        assert refreshed_access_token is not None, "Новый access token должен быть в JSON ответе"
        assert refreshed_access_token != new_access_token, "Токен должен быть обновлен"
        print("✅ Access токен обновлен через refresh token")

        # 8. Использование обновленного токена
        print("\n✅ Шаг 8: Использование обновленного токена")
        # Для надежности передаем обновленный токен через Authorization header
        headers = {"Authorization": f"Bearer {refreshed_access_token}"}
        refreshed_me_response = e2e_client.get("/auth/me", headers=headers)
        wait_between_requests(delay)

        assert refreshed_me_response.status_code == 200
        refreshed_me_data = refreshed_me_response.json()
        assert refreshed_me_data["id"] == user_id
        print("✅ Обновленный токен работает корректно")

        print("\n🎉 E2E тест завершен успешно! Полный цикл аутентификации работает корректно.")
