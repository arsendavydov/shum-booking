import pytest
from datetime import date, timedelta


@pytest.mark.hotels
class TestHotels:
    """Эндпоинты отелей"""
    
    def test_get_hotel_by_id(self, client, created_hotel_ids):
        """Получение отеля по ID"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.get(f"/hotels/{hotel_id}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "id" in data
        assert "title" in data
        assert "address" in data
        assert "city" in data
        assert "country" in data
        assert isinstance(data["city"], str) or data["city"] is None
        assert isinstance(data["country"], str) or data["country"] is None
        assert "postal_code" in data
        assert "check_in_time" in data
        assert "check_out_time" in data
        assert data["id"] == hotel_id
    
    def test_get_hotel_by_id_nonexistent(self, client):
        """Получение несуществующего отеля"""
        response = client.get("/hotels/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "не найден" in data["detail"].lower() or "not found" in data["detail"].lower()
    
    def test_get_hotel_by_id_invalid(self, client):
        """Получение отеля с невалидным ID"""
        response = client.get("/hotels/invalid_id")
        assert response.status_code == 422
    
    def test_create_hotel(self, client, test_prefix, created_hotel_ids):
        """Создание отеля"""
        response = client.post(
            "/hotels",
            json={"title": f"{test_prefix} Тестовый Отель", "city": "Москва", "address": f"{test_prefix} Тестовая улица, 1", "postal_code": "101000"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
        
        today = date.today()
        date_from = today + timedelta(days=1)
        date_to = today + timedelta(days=3)
        response = client.get(
            "/hotels",
            params={"title": f"{test_prefix} Тестовый Отель", "per_page": 20, "page": 1}
        )
        if response.status_code == 200 and response.json():
            test_hotel_id = response.json()[0]["id"]
            created_hotel_ids.append(test_hotel_id)
    
    def test_create_hotel_missing_title(self, client):
        """Создание отеля без title"""
        response = client.post(
            "/hotels",
            json={"city": "Москва", "address": "Тестовая улица, 1"}
        )
        assert response.status_code == 422
    
    def test_create_hotel_missing_city(self, client):
        """Создание отеля без city"""
        response = client.post(
            "/hotels",
            json={"title": "Тест Отель", "address": "Тестовая улица, 1"}
        )
        assert response.status_code == 422
    
    def test_create_hotel_missing_address(self, client):
        """Создание отеля без address"""
        response = client.post(
            "/hotels",
            json={"title": "Тест Отель", "city": "Москва"}
        )
        assert response.status_code == 422
    
    def test_create_hotel_invalid_city(self, client):
        """Создание отеля с несуществующим городом"""
        response = client.post(
            "/hotels",
            json={"title": "Тест Отель", "city": "НесуществующийГород", "address": "Тестовая улица, 1"}
        )
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]
    
    def test_create_hotel_empty_body(self, client):
        """Создание отеля с пустым body"""
        response = client.post("/hotels", json={})
        assert response.status_code == 422
    
    def test_update_hotel(self, client, created_hotel_ids):
        """Обновление отеля"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.put(
            f"/hotels/{hotel_id}",
            json={"title": "Обновленный Отель", "city": "Москва", "address": "Обновленный адрес, 1", "postal_code": "101001"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
    
    def test_update_hotel_missing_title(self, client, created_hotel_ids):
        """Обновление отеля без title"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.put(
            f"/hotels/{hotel_id}",
            json={"city": "Москва", "address": "Обновленный адрес, 1"}
        )
        assert response.status_code == 422
    
    def test_update_hotel_missing_city(self, client, created_hotel_ids):
        """Обновление отеля без city"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.put(
            f"/hotels/{hotel_id}",
            json={"title": "Обновленный Отель", "address": "Обновленный адрес, 1"}
        )
        assert response.status_code == 422
    
    def test_update_hotel_missing_address(self, client, created_hotel_ids):
        """Обновление отеля без address"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.put(
            f"/hotels/{hotel_id}",
            json={"title": "Обновленный Отель", "city": "Москва"}
        )
        assert response.status_code == 422
    
    def test_update_nonexistent_hotel(self, client):
        """Обновление несуществующего отеля"""
        response = client.put(
            "/hotels/99999",
            json={"title": "Test", "city": "Москва", "address": "Test address", "postal_code": "101002"}
        )
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]
    
    def test_update_hotel_invalid_city(self, client, created_hotel_ids):
        """Обновление отеля с несуществующим городом"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.put(
            f"/hotels/{hotel_id}",
            json={"title": "Test", "city": "НесуществующийГород", "address": "Test address"}
        )
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]
    
    def test_partial_update_hotel_title(self, client, created_hotel_ids):
        """Частичное обновление title отеля"""
        if len(created_hotel_ids) <= 1:
            return
        
        hotel_id = created_hotel_ids[1]
        response = client.patch(
            f"/hotels/{hotel_id}",
            json={"title": "Частично Обновленный Отель"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
    
    def test_partial_update_hotel_address(self, client, created_hotel_ids):
        """Частичное обновление address отеля"""
        if len(created_hotel_ids) <= 1:
            return
        
        hotel_id = created_hotel_ids[1]
        response = client.patch(
            f"/hotels/{hotel_id}",
            json={"address": "Новый адрес, 1"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
    
    def test_partial_update_hotel_postal_code(self, client, created_hotel_ids):
        """Частичное обновление postal_code отеля"""
        if len(created_hotel_ids) <= 1:
            return
        
        hotel_id = created_hotel_ids[1]
        response = client.patch(
            f"/hotels/{hotel_id}",
            json={"postal_code": "101004"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
        
        get_response = client.get(f"/hotels/{hotel_id}")
        assert get_response.status_code == 200
        assert get_response.json()["postal_code"] == "101004"
    
    def test_partial_update_hotel_city(self, client, created_hotel_ids):
        """Частичное обновление city отеля"""
        if len(created_hotel_ids) <= 1:
            return
        
        hotel_id = created_hotel_ids[1]
        response = client.patch(
            f"/hotels/{hotel_id}",
            json={"city": "Москва"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
    
    def test_partial_update_hotel_both_fields(self, client, created_hotel_ids):
        """Частичное обновление нескольких полей отеля"""
        if len(created_hotel_ids) <= 2:
            return
        
        hotel_id = created_hotel_ids[2]
        response = client.patch(
            f"/hotels/{hotel_id}",
            json={"title": "Полностью Обновленный", "city": "Москва", "address": "Полностью Новый адрес, 1", "postal_code": "101003"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
    
    def test_partial_update_hotel_invalid_city(self, client, created_hotel_ids):
        """Частичное обновление отеля с несуществующим городом"""
        if len(created_hotel_ids) <= 1:
            return
        
        hotel_id = created_hotel_ids[1]
        response = client.patch(
            f"/hotels/{hotel_id}",
            json={"city": "НесуществующийГород"}
        )
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]
    
    def test_partial_update_hotel_empty_body(self, client, created_hotel_ids):
        """Частичное обновление отеля с пустым body"""
        if len(created_hotel_ids) <= 1:
            return
        
        hotel_id = created_hotel_ids[1]
        response = client.patch(f"/hotels/{hotel_id}", json={})
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
    
    def test_partial_update_nonexistent_hotel(self, client):
        """Частичное обновление несуществующего отеля"""
        response = client.patch("/hotels/99999", json={"title": "Test"})
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]
    
    def test_delete_hotel(self, client, created_hotel_ids):
        """Удаление отеля"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.delete(f"/hotels/{hotel_id}")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
        created_hotel_ids.remove(hotel_id)
    
    def test_delete_nonexistent_hotel(self, client):
        """Удаление несуществующего отеля"""
        response = client.delete("/hotels/99999")
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]

