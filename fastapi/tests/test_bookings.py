import pytest
import httpx
import time
from datetime import date, timedelta
from tests.conftest import TEST_PASSWORD


@pytest.mark.bookings
class TestBookings:
    """Тесты для эндпоинтов бронирований"""
    
    def test_create_booking(
        self, client, created_hotel_ids, created_user_ids, 
        created_booking_ids, created_booking_user_map, test_prefix
    ):
        """Тест создания бронирования"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        room_id = rooms_response.json()[0]["id"]
        
        unique_email = f"{test_prefix}_booking_user_{int(time.time() * 1000)}@example.com"
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
                "password": TEST_PASSWORD
            }
        )
        assert login_response.status_code == 200
        
        today = date.today()
        date_from = today + timedelta(days=1)
        date_to = today + timedelta(days=3)
        
        booking_data = {
            "room_id": room_id,
            "date_from": str(date_from),
            "date_to": str(date_to)
        }
        
        response = client.post("/bookings", json=booking_data)
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
        
        my_bookings_response = client.get("/bookings/me")
        if my_bookings_response.status_code == 200:
            my_bookings = my_bookings_response.json()
            for booking in my_bookings:
                if booking["room_id"] == room_id and booking["date_from"] == str(date_from) and booking["date_to"] == str(date_to):
                    booking_id = booking["id"]
                    created_booking_ids.append(booking_id)
                    created_booking_user_map[booking_id] = (user_data["id"], unique_email)
                    break
    
    def test_create_booking_invalid_dates(
        self, client, created_hotel_ids, created_user_ids, test_prefix
    ):
        """Тест создания бронирования с некорректными датами"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        room_id = rooms_response.json()[0]["id"]
        
        unique_email = f"{test_prefix}_booking_invalid_{int(time.time() * 1000)}@example.com"
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
                "password": TEST_PASSWORD
            }
        )
        assert login_response.status_code == 200
        
        today = date.today()
        booking_data = {
            "room_id": room_id,
            "date_from": str(today + timedelta(days=3)),
            "date_to": str(today + timedelta(days=1))
        }
        
        response = client.post("/bookings", json=booking_data)
        assert response.status_code == 400
        assert "дата заезда должна быть раньше" in response.json()["detail"].lower()
    
    def test_create_booking_nonexistent_room(
        self, client, created_user_ids, test_prefix
    ):
        """Тест создания бронирования с несуществующим номером"""
        unique_email = f"{test_prefix}_booking_nonexistent_room_{int(time.time() * 1000)}@example.com"
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
                "password": TEST_PASSWORD
            }
        )
        assert login_response.status_code == 200
        
        today = date.today()
        date_from = today + timedelta(days=1)
        date_to = today + timedelta(days=3)
        
        booking_data = {
            "room_id": 99999,
            "date_from": str(date_from),
            "date_to": str(date_to)
        }
        
        response = client.post("/bookings", json=booking_data)
        assert response.status_code == 404
        assert "номер не найден" in response.json()["detail"].lower()
    
    def test_create_booking_unauthorized(self, client, created_hotel_ids):
        """Тест создания бронирования без аутентификации"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        room_id = rooms_response.json()[0]["id"]
        
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        
        today = date.today()
        date_from = today + timedelta(days=1)
        date_to = today + timedelta(days=3)
        
        booking_data = {
            "room_id": room_id,
            "date_from": str(date_from),
            "date_to": str(date_to)
        }
        
        response = test_client.post("/bookings", json=booking_data)
        assert response.status_code == 401
        
        test_client.close()
    
    def test_get_all_bookings(self, client):
        """Тест получения всех бронирований"""
        response = client.get("/bookings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_my_bookings(
        self, client, created_hotel_ids, created_user_ids, 
        created_booking_ids, created_booking_user_map, test_prefix
    ):
        """Тест получения своих бронирований"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        room_id = rooms_response.json()[0]["id"]
        
        unique_email = f"{test_prefix}_my_bookings_{int(time.time() * 1000)}@example.com"
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
                "password": TEST_PASSWORD
            }
        )
        assert login_response.status_code == 200
        
        today = date.today()
        date_from = today + timedelta(days=50)
        date_to = today + timedelta(days=52)
        
        booking_data = {
            "room_id": room_id,
            "date_from": str(date_from),
            "date_to": str(date_to)
        }
        
        create_response = client.post("/bookings", json=booking_data)
        assert create_response.status_code == 200
        
        my_bookings_response = client.get("/bookings/me")
        assert my_bookings_response.status_code == 200
        my_bookings = my_bookings_response.json()
        assert isinstance(my_bookings, list)
        assert len(my_bookings) >= 1
        
        for booking in my_bookings:
            if booking["room_id"] == room_id and booking["date_from"] == str(date_from) and booking["date_to"] == str(date_to):
                booking_id = booking["id"]
                created_booking_ids.append(booking_id)
                created_booking_user_map[booking_id] = (user_data["id"], unique_email)
                break
    
    def test_get_my_bookings_unauthorized(self, client):
        """Тест получения своих бронирований без аутентификации"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        response = test_client.get("/bookings/me")
        assert response.status_code == 401
        test_client.close()
    
    def test_delete_booking_nonexistent(
        self, client, created_user_ids, test_prefix
    ):
        """Тест удаления несуществующего бронирования"""
        unique_email = f"{test_prefix}_delete_nonexistent_{int(time.time() * 1000)}@example.com"
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
                "password": TEST_PASSWORD
            }
        )
        assert login_response.status_code == 200
        
        response = client.delete("/bookings/99999")
        assert response.status_code == 404
        assert "бронирование не найдено" in response.json()["detail"].lower()

