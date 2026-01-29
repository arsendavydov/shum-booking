import pytest
import time
from tests.conftest import TEST_EXAMPLE_EMAIL_DOMAIN


@pytest.mark.users
class TestUsers:
    """Тесты для эндпоинтов пользователей"""
    
    def test_get_all_users(self, client):
        """Тест получения всех пользователей"""
        response = client.get("/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
    
    def test_get_user_by_id(self, client, created_user_ids):
        """Тест получения пользователя по ID"""
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
        """Тест получения несуществующего пользователя по ID"""
        response = client.get("/users/99999")
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]
    
    def test_get_user_by_email(self, client, created_user_ids):
        """Тест получения пользователя по email"""
        if not created_user_ids:
            return
        
        response = client.get("/users?email=test@{TEST_EXAMPLE_EMAIL_DOMAIN}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert data[0]["email"] == "test@{TEST_EXAMPLE_EMAIL_DOMAIN}"
    
    def test_update_user(self, client, test_prefix, created_user_ids):
        """Тест обновления пользователя"""
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
                "last_name": "Пользователь"
            }
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
    
    def test_update_nonexistent_user(self, client):
        """Тест обновления несуществующего пользователя"""
        response = client.put(
            "/users/99999",
            json={
                "email": "test@{TEST_EXAMPLE_EMAIL_DOMAIN}",
                "hashed_password": "pass123"
            }
        )
        assert response.status_code == 404
    
    def test_partial_update_user(self, client, created_user_ids):
        """Тест частичного обновления пользователя"""
        if not created_user_ids:
            return
        
        user_id = created_user_ids[0]
        response = client.patch(
            f"/users/{user_id}",
            json={"first_name": "Частично", "last_name": "Обновленный"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
    
    def test_partial_update_nonexistent_user(self, client):
        """Тест частичного обновления несуществующего пользователя"""
        response = client.patch(
            "/users/99999",
            json={"first_name": "Test"}
        )
        assert response.status_code == 404
    
    def test_delete_user(self, client, created_user_ids):
        """Тест удаления пользователя"""
        if not created_user_ids:
            return
        
        user_id = created_user_ids[-1]
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
        created_user_ids.remove(user_id)
    
    def test_delete_nonexistent_user(self, client):
        """Тест удаления несуществующего пользователя"""
        response = client.delete("/users/99999")
        assert response.status_code == 404

