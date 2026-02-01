import time

import pytest

from tests.api_tests import TEST_EXAMPLE_EMAIL_DOMAIN


@pytest.mark.users
class TestUsers:
    """Эндпоинты пользователей"""

    def test_get_all_users(self, client):
        """Получение всех пользователей"""
        response = client.get("/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_get_user_by_id(self, client, created_user_ids):
        """Получение пользователя по ID"""
        if not created_user_ids:
            return

        user_id = created_user_ids[0]
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert data["id"] == user_id

    def test_get_user_by_id_nonexistent(self, client):
        """Получение несуществующего пользователя по ID"""
        response = client.get("/users/99999")
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]

    def test_get_user_by_email(self, client, created_user_ids):
        """Получение пользователя по email"""
        if not created_user_ids:
            return

        test_email = f"test@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        response = client.get(f"/users?email={test_email}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert data[0]["email"] == test_email

    def test_update_user(self, client, test_prefix, created_user_ids):
        """Обновление пользователя"""
        if not created_user_ids:
            return

        user_id = created_user_ids[0]
        unique_email = f"{test_prefix}_updated_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        response = client.put(
            f"/users/{user_id}",
            json={
                "email": unique_email,
                "hashed_password": "newhashedpass123",
                "first_name": "Обновленный",
                "last_name": "Пользователь",
            },
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}

    @pytest.mark.parametrize(
        "method,endpoint,json_data",
        [
            ("put", "/users/99999", {"email": f"test@{TEST_EXAMPLE_EMAIL_DOMAIN}", "hashed_password": "pass123"}),
            ("patch", "/users/99999", {"first_name": "Test"}),
            ("delete", "/users/99999", None),
        ],
    )
    def test_user_nonexistent_operations(self, client, method, endpoint, json_data):
        """Операции с несуществующим пользователем"""
        if json_data is None:
            response = client.delete(endpoint)
        elif method == "put":
            response = client.put(endpoint, json=json_data)
        else:
            response = client.patch(endpoint, json=json_data)

        assert response.status_code == 404

    def test_partial_update_user(self, client, created_user_ids):
        """Частичное обновление пользователя"""
        if not created_user_ids:
            return

        user_id = created_user_ids[0]
        response = client.patch(f"/users/{user_id}", json={"first_name": "Частично", "last_name": "Обновленный"})
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}

    def test_delete_user(self, client, created_user_ids):
        """Удаление пользователя"""
        if not created_user_ids:
            return

        user_id = created_user_ids[-1]
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
        created_user_ids.remove(user_id)
