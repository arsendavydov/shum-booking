"""
E2E тест: Полный цикл поиска отеля.

Проверяет полный сценарий поиска и просмотра отеля:
1. Получение списка стран
2. Поиск городов в стране
3. Поиск отелей в городе
4. Просмотр деталей отеля
5. Просмотр номеров отеля
6. Просмотр удобств
"""

import pytest

from tests.e2e_tests.conftest import wait_between_requests


@pytest.mark.e2e
@pytest.mark.slow
class TestHotelSearchFlow:
    """E2E тесты для полного цикла поиска отеля"""

    def test_hotel_search_journey(self, e2e_client, delay):
        """Полный путь поиска отеля: страна → город → отель → номера → удобства"""

        # 1. Получение списка стран
        print("\n🌍 Шаг 1: Получение списка стран")
        countries_response = e2e_client.get("/countries")
        wait_between_requests(delay)

        assert countries_response.status_code == 200
        countries = countries_response.json()
        assert len(countries) > 0, "Должна быть хотя бы одна страна"
        country_id = countries[0]["id"]
        country_name = countries[0]["name"]  # Используем 'name', а не 'title'
        print(f"✅ Найдено стран: {len(countries)}, выбрана: {country_name} (ID={country_id})")

        # 2. Получение деталей страны
        print("\n📋 Шаг 2: Детали страны")
        country_detail_response = e2e_client.get(f"/countries/{country_id}")
        wait_between_requests(delay)

        assert country_detail_response.status_code == 200
        country_detail = country_detail_response.json()
        assert country_detail["id"] == country_id
        print("✅ Детали страны получены")

        # 3. Поиск городов в стране
        print("\n🏙️ Шаг 3: Поиск городов в стране")
        cities_response = e2e_client.get(f"/cities?country_id={country_id}")
        wait_between_requests(delay)

        assert cities_response.status_code == 200
        cities = cities_response.json()
        assert len(cities) > 0, f"Должен быть хотя бы один город в стране {country_id}"
        city_id = cities[0]["id"]
        city_name = cities[0]["name"]  # Используем 'name', а не 'title'
        print(f"✅ Найдено городов: {len(cities)}, выбран: {city_name} (ID={city_id})")

        # 4. Получение деталей города
        print("\n📋 Шаг 4: Детали города")
        city_detail_response = e2e_client.get(f"/cities/{city_id}")
        wait_between_requests(delay)

        assert city_detail_response.status_code == 200
        city_detail = city_detail_response.json()
        assert city_detail["id"] == city_id
        print("✅ Детали города получены")

        # 5. Поиск отелей в городе
        print("\n🏨 Шаг 5: Поиск отелей в городе")
        hotels_response = e2e_client.get(f"/hotels?city_id={city_id}")
        wait_between_requests(delay)

        assert hotels_response.status_code == 200
        hotels = hotels_response.json()
        assert len(hotels) > 0, f"Должен быть хотя бы один отель в городе {city_id}"
        hotel_id = hotels[0]["id"]
        hotel_name = hotels[0]["title"]
        print(f"✅ Найдено отелей: {len(hotels)}, выбран: {hotel_name} (ID={hotel_id})")

        # 6. Получение деталей отеля
        print("\n📋 Шаг 6: Детали отеля")
        hotel_detail_response = e2e_client.get(f"/hotels/{hotel_id}")
        wait_between_requests(delay)

        assert hotel_detail_response.status_code == 200
        hotel_detail = hotel_detail_response.json()
        assert hotel_detail["id"] == hotel_id
        print(f"✅ Детали отеля получены: {hotel_detail.get('title')}")

        # 7. Просмотр номеров в отеле
        print("\n🛏️ Шаг 7: Просмотр номеров в отеле")
        rooms_response = e2e_client.get(f"/hotels/{hotel_id}/rooms")
        wait_between_requests(delay)

        assert rooms_response.status_code == 200
        rooms = rooms_response.json()
        assert len(rooms) > 0, f"Должен быть хотя бы один номер в отеле {hotel_id}"
        room_id = rooms[0]["id"]
        room_title = rooms[0]["title"]
        print(f"✅ Найдено номеров: {len(rooms)}, выбран: {room_title} (ID={room_id})")

        # 8. Получение деталей номера
        print("\n📋 Шаг 8: Детали номера")
        room_detail_response = e2e_client.get(f"/hotels/{hotel_id}/rooms/{room_id}")
        wait_between_requests(delay)

        assert room_detail_response.status_code == 200
        room_detail = room_detail_response.json()
        assert room_detail["id"] == room_id
        print(f"✅ Детали номера получены: цена={room_detail.get('price')}")

        # 9. Получение списка удобств
        print("\n✨ Шаг 9: Получение списка удобств")
        facilities_response = e2e_client.get("/facilities")
        wait_between_requests(delay)

        assert facilities_response.status_code == 200
        facilities = facilities_response.json()
        print(f"✅ Найдено удобств: {len(facilities)}")

        # 10. Проверка удобств в номере
        if "facilities" in room_detail and len(room_detail["facilities"]) > 0:
            print("\n✨ Шаг 10: Удобства в номере")
            room_facilities = room_detail["facilities"]
            print(f"✅ В номере доступно удобств: {len(room_facilities)}")
            for facility in room_facilities[:3]:  # Показываем первые 3
                print(f"   - {facility.get('title')}")

        print("\n🎉 E2E тест завершен успешно! Полный цикл поиска отеля работает корректно.")
