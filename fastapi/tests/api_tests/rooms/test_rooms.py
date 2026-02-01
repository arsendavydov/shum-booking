import pytest
from datetime import date, timedelta


@pytest.mark.rooms
class TestRooms:
    """Эндпоинты номеров"""
    
    def test_get_all_rooms(self, client, created_hotel_ids):
        """Получение всех номеров отеля"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.get(f"/hotels/{hotel_id}/rooms")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_room_by_id(self, client, created_hotel_ids):
        """Получение номера по ID"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code == 200:
            rooms = rooms_response.json()
            if rooms:
                room_id = rooms[0]["id"]
                response = client.get(f"/hotels/{hotel_id}/rooms/{room_id}")
                assert response.status_code == 200
                data = response.json()
                assert "id" in data
                assert "hotel_id" in data
                assert "title" in data
                assert data["id"] == room_id
                assert data["hotel_id"] == hotel_id
    
    def test_get_room_by_id_nonexistent(self, client, created_hotel_ids):
        """Получение несуществующего номера по ID"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.get(f"/hotels/{hotel_id}/rooms/99999")
        assert response.status_code == 404
        assert "не найд" in response.json()["detail"]
    
    def test_get_rooms_by_hotel_id(self, client, created_hotel_ids):
        """Получение номеров по hotel_id"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.get(f"/hotels/{hotel_id}/rooms")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for room in data:
            assert room["hotel_id"] == hotel_id
    
    def test_get_rooms_by_title(self, client, created_hotel_ids, test_prefix):
        """Получение номеров по title"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.get(f"/hotels/{hotel_id}/rooms?title={test_prefix} Стандартный")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_room(self, client, created_hotel_ids, created_room_ids, test_prefix):
        """Создание номера"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.post(
            f"/hotels/{hotel_id}/rooms",
            json={
                "title": f"{test_prefix} Тестовая комната",
                "description": f"{test_prefix} Описание тестовой комнаты",
                "price": 2500,
                "quantity": 2
            }
        )
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
        
        get_response = client.get(f"/hotels/{hotel_id}/rooms?title={test_prefix} Тестовая")
        if get_response.status_code == 200 and get_response.json():
            created_room_ids.append(get_response.json()[0]["id"])
    
    def test_create_room_missing_fields(self, client, created_hotel_ids, test_prefix):
        """Создание номера с неполными данными"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        response = client.post(
            f"/hotels/{hotel_id}/rooms",
            json={"title": f"{test_prefix} Неполная комната"}
        )
        assert response.status_code == 422
    
    def test_update_room(self, client, created_hotel_ids, test_prefix):
        """Обновление номера"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code == 200:
            rooms = rooms_response.json()
            if rooms:
                room_id = rooms[0]["id"]
                response = client.put(
                    f"/hotels/{hotel_id}/rooms/{room_id}",
                    json={
                        "title": f"{test_prefix} Обновленная комната",
                        "description": f"{test_prefix} Новое описание",
                        "price": 4000,
                        "quantity": 4
                    }
                )
                assert response.status_code == 200
                assert response.json() == {"status": "OK"}
    
    @pytest.mark.parametrize("method,json_data", [
        ("put", {"title": "Test", "price": 1000, "quantity": 1}),
        ("patch", {"title": "Test"}),
        ("delete", None),
    ])
    def test_room_nonexistent_operations(self, client, created_hotel_ids, method, json_data):
        """Операции с несуществующим номером"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        endpoint = f"/hotels/{hotel_id}/rooms/99999"
        
        if json_data is None:
            response = client.delete(endpoint)
        elif method == "put":
            response = client.put(endpoint, json=json_data)
        else:
            response = client.patch(endpoint, json=json_data)
        
        assert response.status_code == 404
    
    def test_partial_update_room(self, client, created_hotel_ids, test_prefix):
        """Частичное обновление номера"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code == 200:
            rooms = rooms_response.json()
            if rooms:
                room_id = rooms[0]["id"]
                response = client.patch(
                    f"/hotels/{hotel_id}/rooms/{room_id}",
                    json={"title": f"{test_prefix} Частично обновленная", "price": 3500}
                )
                assert response.status_code == 200
                assert response.json() == {"status": "OK"}
    
    def test_delete_room(self, client, created_hotel_ids, created_room_ids):
        """Удаление номера"""
        if not created_room_ids or not created_hotel_ids:
            return
        
        room_id = created_room_ids[-1]
        hotel_id = created_hotel_ids[-1]
        response = client.delete(f"/hotels/{hotel_id}/rooms/{room_id}")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
        created_room_ids.remove(room_id)
    
    def test_get_available_rooms(self, client, created_hotel_ids):
        """Получение доступных номеров на период"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        today = date.today()
        date_from = today + timedelta(days=100)
        date_to = today + timedelta(days=103)
        
        response = client.get(
            f"/hotels/{hotel_id}/rooms/available",
            params={"date_from": str(date_from), "date_to": str(date_to)}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

