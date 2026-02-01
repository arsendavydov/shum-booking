import pytest
import httpx
import time
from datetime import date, timedelta
from tests.api_tests import TEST_PASSWORD, TEST_EXAMPLE_EMAIL_DOMAIN


@pytest.mark.bookings
class TestBookings:
    """Эндпоинты бронирований"""
    
    def test_create_booking(
        self, client, created_hotel_ids, created_user_ids, 
        created_booking_ids, created_booking_user_map, test_prefix
    ):
        """Создание бронирования"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        room_id = rooms_response.json()[0]["id"]
        
        unique_email = f"{test_prefix}_booking_user_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
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
        """Создание бронирования с некорректными датами"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        room_id = rooms_response.json()[0]["id"]
        
        unique_email = f"{test_prefix}_booking_invalid_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
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
        """Создание бронирования с несуществующим номером"""
        unique_email = f"{test_prefix}_booking_nonexistent_room_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
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
        """Создание бронирования без аутентификации"""
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
        """Получение всех бронирований"""
        response = client.get("/bookings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_my_bookings(
        self, client, created_hotel_ids, created_user_ids, 
        created_booking_ids, created_booking_user_map, test_prefix
    ):
        """Получение своих бронирований"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        room_id = rooms_response.json()[0]["id"]
        
        unique_email = f"{test_prefix}_my_bookings_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
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
        """Получение своих бронирований без аутентификации"""
        test_client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)
        response = test_client.get("/bookings/me")
        assert response.status_code == 401
        test_client.close()
    
    def test_delete_booking_nonexistent(
        self, client, created_user_ids, test_prefix
    ):
        """Удаление несуществующего бронирования"""
        unique_email = f"{test_prefix}_delete_nonexistent_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
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
    
    def test_create_booking_all_rooms_booked(
        self, client, created_hotel_ids, created_user_ids, 
        created_booking_ids, created_booking_user_map, test_prefix
    ):
        """Попытка забронировать номер, когда все номера данного типа уже забронированы"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        # Находим номер с quantity=1 (президентский люкс)
        rooms = rooms_response.json()
        room = None
        for r in rooms:
            if r.get("quantity", 0) == 1:
                room = r
                break
        
        if not room:
            return
        
        room_id = room["id"]
        room_quantity = room["quantity"]
        
        today = date.today()
        date_from = today + timedelta(days=100)
        date_to = today + timedelta(days=102)
        
        # Создаем пользователей и бронируем все доступные номера
        booking_ids = []
        for i in range(room_quantity):
            unique_email = f"{test_prefix}_full_booking_{i}_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
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
            
            booking_data = {
                "room_id": room_id,
                "date_from": str(date_from),
                "date_to": str(date_to)
            }
            
            booking_response = client.post("/bookings", json=booking_data)
            assert booking_response.status_code == 200
            
            # Сохраняем ID бронирования для очистки
            my_bookings = client.get("/bookings/me").json()
            for booking in my_bookings:
                if booking["room_id"] == room_id:
                    booking_ids.append(booking["id"])
                    created_booking_user_map[booking["id"]] = (user_data["id"], unique_email)
                    break
        
        # Пытаемся забронировать еще один номер (должно быть отклонено)
        unique_email = f"{test_prefix}_full_booking_extra_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
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
        
        booking_data = {
            "room_id": room_id,
            "date_from": str(date_from),
            "date_to": str(date_to)
        }
        
        response = client.post("/bookings", json=booking_data)
        assert response.status_code == 409
        assert "все номера" in response.json()["detail"].lower()
        
        # Сохраняем все созданные бронирования для очистки
        created_booking_ids.extend(booking_ids)
    
    def test_create_booking_multiple_rooms_available(
        self, client, created_hotel_ids, created_user_ids, 
        created_booking_ids, created_booking_user_map, test_prefix
    ):
        """Бронирование нескольких номеров одного типа, когда quantity позволяет"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        # Находим номер с quantity >= 3
        rooms = rooms_response.json()
        room = None
        for r in rooms:
            if r.get("quantity", 0) >= 3:
                room = r
                break
        
        if not room:
            return
        
        room_id = room["id"]
        room_quantity = room["quantity"]
        
        today = date.today()
        date_from = today + timedelta(days=150)
        date_to = today + timedelta(days=152)
        
        # Бронируем несколько номеров (но не все)
        max_bookings = min(room_quantity - 1, 2)  # Оставляем хотя бы один свободный
        
        booking_ids = []
        for i in range(max_bookings):
            unique_email = f"{test_prefix}_multi_booking_{i}_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
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
            
            booking_data = {
                "room_id": room_id,
                "date_from": str(date_from),
                "date_to": str(date_to)
            }
            
            booking_response = client.post("/bookings", json=booking_data)
            assert booking_response.status_code == 200
            
            # Сохраняем ID бронирования
            my_bookings = client.get("/bookings/me").json()
            for booking in my_bookings:
                if booking["room_id"] == room_id and booking["date_from"] == str(date_from):
                    booking_ids.append(booking["id"])
                    created_booking_user_map[booking["id"]] = (user_data["id"], unique_email)
                    break
        
        # Проверяем, что все бронирования созданы успешно
        assert len(booking_ids) == max_bookings
        
        # Сохраняем все созданные бронирования для очистки
        created_booking_ids.extend(booking_ids)
    
    def test_create_booking_after_deletion(
        self, client, created_hotel_ids, created_user_ids, 
        created_booking_ids, created_booking_user_map, test_prefix
    ):
        """Бронирование номера после освобождения (удаления предыдущего бронирования)"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        rooms_response = client.get(f"/hotels/{hotel_id}/rooms")
        if rooms_response.status_code != 200 or not rooms_response.json():
            return
        
        # Находим номер с quantity=1
        rooms = rooms_response.json()
        room = None
        for r in rooms:
            if r.get("quantity", 0) == 1:
                room = r
                break
        
        if not room:
            return
        
        room_id = room["id"]
        
        today = date.today()
        date_from = today + timedelta(days=200)
        date_to = today + timedelta(days=202)
        
        # Создаем первое бронирование
        unique_email1 = f"{test_prefix}_delete_test_1_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        register_response = client.post(
            "/auth/register",
            json={
                "email": unique_email1,
                "password": TEST_PASSWORD
            }
        )
        assert register_response.status_code == 201
        user_data1 = register_response.json()
        created_user_ids.append(user_data1["id"])
        
        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email1,
                "password": TEST_PASSWORD
            }
        )
        assert login_response.status_code == 200
        
        booking_data = {
            "room_id": room_id,
            "date_from": str(date_from),
            "date_to": str(date_to)
        }
        
        booking_response = client.post("/bookings", json=booking_data)
        assert booking_response.status_code == 200
        
        # Получаем ID созданного бронирования
        my_bookings = client.get("/bookings/me").json()
        booking_id = None
        for booking in my_bookings:
            if booking["room_id"] == room_id and booking["date_from"] == str(date_from):
                booking_id = booking["id"]
                created_booking_user_map[booking_id] = (user_data1["id"], unique_email1)
                break
        
        assert booking_id is not None
        
        # Пытаемся забронировать тот же номер другим пользователем (должно быть отклонено)
        unique_email2 = f"{test_prefix}_delete_test_2_{int(time.time() * 1000)}@{TEST_EXAMPLE_EMAIL_DOMAIN}"
        register_response = client.post(
            "/auth/register",
            json={
                "email": unique_email2,
                "password": TEST_PASSWORD
            }
        )
        assert register_response.status_code == 201
        user_data2 = register_response.json()
        created_user_ids.append(user_data2["id"])
        
        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email2,
                "password": TEST_PASSWORD
            }
        )
        assert login_response.status_code == 200
        
        response = client.post("/bookings", json=booking_data)
        assert response.status_code == 409
        assert "все номера" in response.json()["detail"].lower()
        
        # Удаляем первое бронирование
        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email1,
                "password": TEST_PASSWORD
            }
        )
        assert login_response.status_code == 200
        
        delete_response = client.delete(f"/bookings/{booking_id}")
        assert delete_response.status_code == 200
        
        # Теперь второй пользователь должен иметь возможность забронировать
        login_response = client.post(
            "/auth/login",
            json={
                "email": unique_email2,
                "password": TEST_PASSWORD
            }
        )
        assert login_response.status_code == 200
        
        booking_response = client.post("/bookings", json=booking_data)
        assert booking_response.status_code == 200
        
        # Сохраняем новое бронирование для очистки
        my_bookings = client.get("/bookings/me").json()
        for booking in my_bookings:
            if booking["room_id"] == room_id and booking["date_from"] == str(date_from):
                new_booking_id = booking["id"]
                created_booking_ids.append(new_booking_id)
                created_booking_user_map[new_booking_id] = (user_data2["id"], unique_email2)
                break

