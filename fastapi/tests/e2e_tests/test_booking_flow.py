"""
E2E тест: Полный цикл бронирования.

Проверяет полный пользовательский сценарий:
1. Регистрация пользователя
2. Поиск страны и города
3. Поиск отеля
4. Просмотр номеров
5. Создание бронирования
6. Просмотр своих бронирований
7. Отмена бронирования
"""

import pytest

from tests.e2e_tests.conftest import TEST_PASSWORD, wait_between_requests


@pytest.mark.e2e
@pytest.mark.slow
class TestBookingFlow:
    """E2E тесты для полного цикла бронирования"""

    def test_full_booking_journey(self, e2e_client, test_user_email, delay):
        """Полный путь пользователя: от регистрации до бронирования"""

        # 1. Регистрация нового пользователя
        print("\n📝 Шаг 1: Регистрация пользователя")
        register_data = {
            "email": test_user_email,
            "password": TEST_PASSWORD,
            "first_name": "E2E",
            "last_name": "Test",
        }
        register_response = e2e_client.post("/auth/register", json=register_data)
        wait_between_requests(delay)

        assert register_response.status_code == 201, (
            f"Ожидался статус 201, получен {register_response.status_code}: {register_response.text}"
        )
        user_data = register_response.json()
        user_id = user_data["id"]
        assert user_data["email"] == test_user_email
        print(f"✅ Пользователь зарегистрирован: ID={user_id}, email={test_user_email}")

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
        # Получаем access_token из cookies после логина
        access_token = login_response.cookies.get("access_token")
        assert access_token is not None, "Access token должен быть в cookies"

        # 2. Поиск страны
        print("\n🌍 Шаг 2: Поиск страны")
        countries_response = e2e_client.get("/countries")
        wait_between_requests(delay)

        assert countries_response.status_code == 200
        countries = countries_response.json()
        assert len(countries) > 0, "Должна быть хотя бы одна страна"
        country_id = countries[0]["id"]
        country_name = countries[0]["name"]  # Используем 'name', а не 'title'
        print(f"✅ Выбрана страна: {country_name} (ID={country_id})")

        # 3. Поиск города в выбранной стране
        print("\n🏙️ Шаг 3: Поиск города")
        cities_response = e2e_client.get(f"/cities?country_id={country_id}")
        wait_between_requests(delay)

        assert cities_response.status_code == 200
        cities = cities_response.json()
        assert len(cities) > 0, f"Должен быть хотя бы один город в стране {country_id}"
        city_id = cities[0]["id"]
        city_name = cities[0]["name"]  # Используем 'name', а не 'title'
        print(f"✅ Выбран город: {city_name} (ID={city_id})")

        # 4. Поиск отеля в выбранном городе
        print("\n🏨 Шаг 4: Поиск отеля")
        hotels_response = e2e_client.get(f"/hotels?city_id={city_id}")
        wait_between_requests(delay)

        assert hotels_response.status_code == 200
        hotels = hotels_response.json()
        assert len(hotels) > 0, f"Должен быть хотя бы один отель в городе {city_id}"
        hotel_id = hotels[0]["id"]
        hotel_name = hotels[0]["title"]
        print(f"✅ Выбран отель: {hotel_name} (ID={hotel_id})")

        # 5. Просмотр номеров в отеле
        print("\n🛏️ Шаг 5: Просмотр номеров")
        rooms_response = e2e_client.get(f"/hotels/{hotel_id}/rooms")
        wait_between_requests(delay)

        assert rooms_response.status_code == 200
        rooms = rooms_response.json()
        assert len(rooms) > 0, f"Должен быть хотя бы один номер в отеле {hotel_id}"
        room_id = rooms[0]["id"]
        room_title = rooms[0]["title"]
        room_price = rooms[0]["price"]
        print(f"✅ Выбран номер: {room_title} (ID={room_id}, цена={room_price})")

        # 6. Получение деталей номера
        print("\n📋 Шаг 6: Детали номера")
        room_detail_response = e2e_client.get(f"/hotels/{hotel_id}/rooms/{room_id}")
        wait_between_requests(delay)

        assert room_detail_response.status_code == 200
        room_detail = room_detail_response.json()
        assert room_detail["id"] == room_id
        print("✅ Детали номера получены")

        # 7. Создание бронирования (требует авторизации)
        print("\n📅 Шаг 7: Создание бронирования")
        # Устанавливаем токен в cookies для авторизованных запросов
        cookies = {"access_token": access_token}

        # Даты для бронирования (через месяц от текущей даты)
        from datetime import datetime, timedelta

        check_in = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=35)).strftime("%Y-%m-%d")

        # В API бронирования используются поля date_from/date_to
        booking_data = {
            "room_id": room_id,
            "date_from": check_in,
            "date_to": check_out,
        }
        booking_response = e2e_client.post("/bookings", json=booking_data, cookies=cookies)
        wait_between_requests(delay)

        # Эндпоинт возвращает 200 OK с MessageResponse {"status": "OK"}
        assert booking_response.status_code == 200, (
            f"Ожидался статус 200, получен {booking_response.status_code}: {booking_response.text}"
        )
        print(f"✅ Запрос на создание бронирования принят: {booking_response.json()}")

        # 8. Просмотр своих бронирований
        print("\n📋 Шаг 8: Просмотр своих бронирований")
        # Эндпоинт своих бронирований: /bookings/me
        my_bookings_response = e2e_client.get("/bookings/me", cookies=cookies)
        wait_between_requests(delay)

        assert my_bookings_response.status_code == 200
        my_bookings = my_bookings_response.json()
        assert len(my_bookings) > 0, "Должно быть хотя бы одно бронирование"

        # Ищем только что созданное бронирование по room_id и датам
        matching_booking = next(
            (
                b
                for b in my_bookings
                if b["room_id"] == room_id and b["date_from"] == check_in and b["date_to"] == check_out
            ),
            None,
        )
        assert matching_booking is not None, "Созданное бронирование должно быть в списке"
        booking_id = matching_booking["id"]
        assert matching_booking["user_id"] == user_id
        print(f"✅ Бронирование создано: ID={booking_id}, {check_in} - {check_out}")

        print(f"✅ Найдено бронирований: {len(my_bookings)}")

        # 9. Отмена бронирования
        print("\n❌ Шаг 9: Отмена бронирования")
        cancel_response = e2e_client.delete(f"/bookings/{booking_id}", cookies=cookies)
        wait_between_requests(delay)

        assert cancel_response.status_code in [200, 204], (
            f"Ожидался статус 200/204, получен {cancel_response.status_code}"
        )
        print("✅ Бронирование отменено")

        # 10. Проверка, что бронирование удалено
        print("\n✅ Шаг 10: Проверка удаления бронирования")
        check_bookings_response = e2e_client.get("/bookings/me", cookies=cookies)
        wait_between_requests(delay)

        assert check_bookings_response.status_code == 200
        remaining_bookings = check_bookings_response.json()
        assert not any(b["id"] == booking_id for b in remaining_bookings), "Бронирование должно быть удалено"
        print("✅ Бронирование успешно удалено из списка")

        print("\n🎉 E2E тест завершен успешно! Полный цикл бронирования работает корректно.")
