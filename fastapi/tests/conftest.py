import pytest
import httpx
import time
import os
import psycopg2
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path
from dotenv import load_dotenv

BASE_URL = "http://localhost:8001"  # Тестовый FastAPI на порту 8001
TEST_PREFIX = f"TEST_{int(time.time())}"

# Загружаем переменные окружения из .test.env
env_test_path = Path(__file__).resolve().parent.parent.parent / ".test.env"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)

# Тестовые данные из переменных окружения (обязательны для тестов)
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
TEST_EXAMPLE_EMAIL_DOMAIN = os.getenv("TEST_EXAMPLE_EMAIL_DOMAIN", "shum-booking.com")

if not TEST_PASSWORD:
    raise ValueError(
        "Переменная окружения TEST_PASSWORD должна быть установлена в .test.env файле. "
        "Этот пароль используется для создания тестовых пользователей во время тестов."
    )


def cleanup_test_database():
    """Очищает все данные из тестовой БД перед запуском тестов"""
    try:
        # Получаем настройки БД из переменных окружения
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = int(os.getenv("DB_PORT", "5432"))
        db_username = os.getenv("DB_USERNAME", "postgres")
        db_password = os.getenv("DB_PASSWORD", "postgres")
        db_name = os.getenv("DB_NAME", "test")
        
        # Подключаемся к тестовой БД
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_username,
            password=db_password,
            database=db_name
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Отключаем проверку внешних ключей для безопасной очистки
        cursor.execute("SET session_replication_role = 'replica';")
        
        # Получаем список всех таблиц в схеме public, кроме alembic_version
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' AND tablename != 'alembic_version'
            ORDER BY tablename;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        if tables:
            # Очищаем все таблицы с CASCADE для очистки связанных таблиц
            # RESTART IDENTITY сбрасывает автоинкрементные счетчики
            table_list = ', '.join([f'"{table}"' for table in tables])
            cursor.execute(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE;")
            print(f"🧹 Очищено {len(tables)} таблиц в тестовой БД перед запуском тестов")
        
        # Включаем обратно проверку внешних ключей
        cursor.execute("SET session_replication_role = 'origin';")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Ошибка при очистке тестовой БД перед тестами: {e}")



@pytest.fixture(scope="session")
def client():
    """HTTP клиент для тестов"""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        yield client


@pytest.fixture(scope="session")
def test_prefix():
    """Префикс для тестовых данных"""
    return TEST_PREFIX


@pytest.fixture(scope="session", autouse=True)
def cleanup_before_tests():
    """Очищает тестовую БД перед запуском всех тестов"""
    print("🧹 Очистка тестовой БД перед запуском тестов...")
    cleanup_test_database()
    yield


@pytest.fixture(scope="session", autouse=True)
def setup_test_city(client):
    """Создает страну 'Россия' и город 'Москва' в тестовой БД перед запуском тестов через API"""
    try:
        # Проверяем, существует ли страна "Россия"
        countries_response = client.get("/countries", params={"name": "Россия", "page": 1, "per_page": 1})
        country_id = None
        
        if countries_response.status_code == 200:
            countries = countries_response.json()
            for country in countries:
                if country["name"].lower() == "россия":
                    country_id = country["id"]
                    print(f"✅ Страна 'Россия' уже существует с ID: {country_id}")
                    break
        
        # Создаем страну "Россия", если её нет
        if country_id is None:
            country_response = client.post(
                "/countries",
                json={"name": "Россия", "iso_code": "RU"}
            )
            if country_response.status_code == 200:
                # Получаем созданную страну
                countries_response = client.get("/countries", params={"name": "Россия", "page": 1, "per_page": 1})
                if countries_response.status_code == 200:
                    countries = countries_response.json()
                    if countries:
                        country_id = countries[0]["id"]
                        print(f"✅ Создана страна 'Россия' с ID: {country_id}")
        
        # Проверяем, существует ли город "Москва"
        if country_id is not None:
            cities_response = client.get("/cities", params={"name": "Москва", "country_id": country_id, "page": 1, "per_page": 1})
            city_exists = False
            
            if cities_response.status_code == 200:
                cities = cities_response.json()
                for city in cities:
                    if city["name"].lower() == "москва" and city["country_id"] == country_id:
                        city_exists = True
                        print(f"✅ Город 'Москва' уже существует с ID: {city['id']}")
                        break
            
            # Создаем город "Москва", если его нет
            if not city_exists:
                city_response = client.post(
                    "/cities",
                    json={"name": "Москва", "country_id": country_id}
                )
                if city_response.status_code == 200:
                    print(f"✅ Создан город 'Москва'")
                else:
                    error_detail = city_response.json().get("detail", "Unknown error") if city_response.status_code != 200 else ""
                    print(f"⚠️ Не удалось создать город 'Москва': {city_response.status_code} - {error_detail}")
    except Exception as e:
        print(f"⚠️ Ошибка при создании тестовых данных: {e}")
    
    yield
    
    # Cleanup не требуется - данные остаются в БД для других тестов


@pytest.fixture(scope="session")
def created_hotel_ids(client, test_prefix):
    """Создает тестовые отели и возвращает список их ID"""
    hotels = [
        {"title": f"{test_prefix} Отель Москва Центр 001", "city": "Москва", "address": f"{test_prefix} Тверская улица, 1", "postal_code": "101000"},
        {"title": f"{test_prefix} Отель Москва Север 002", "city": "Москва", "address": f"{test_prefix} Ленинградский проспект, 10", "postal_code": "125040"},
        {"title": f"{test_prefix} Отель Москва Юг 003", "city": "Москва", "address": f"{test_prefix} Варшавское шоссе, 5", "postal_code": "117105"},
        {"title": f"{test_prefix} Отель Москва Восток 004", "city": "Москва", "address": f"{test_prefix} Энтузиастов шоссе, 2", "postal_code": "111024"},
        {"title": f"{test_prefix} Отель Москва Запад 005", "city": "Москва", "address": f"{test_prefix} Кутузовский проспект, 50", "postal_code": "121248"},
        {"title": f"{test_prefix} Отель Москва Кремль 006", "city": "Москва", "address": f"{test_prefix} Красная площадь, 20", "postal_code": "109012"},
        {"title": f"{test_prefix} Отель Москва Арбат 007", "city": "Москва", "address": f"{test_prefix} Арбат, 15", "postal_code": "119002"},
        {"title": f"{test_prefix} Отель Москва Сокольники 008", "city": "Москва", "address": f"{test_prefix} Сокольническая площадь, 7", "postal_code": "107113"},
        {"title": f"{test_prefix} Отель Москва Измайлово 009", "city": "Москва", "address": f"{test_prefix} Измайловский проспект, 100", "postal_code": "105187"},
        {"title": f"{test_prefix} Отель Москва ВДНХ 010", "city": "Москва", "address": f"{test_prefix} Проспект Мира, 18", "postal_code": "129223"},
        {"title": f"{test_prefix} Отель Москва Таганка 011", "city": "Москва", "address": f"{test_prefix} Таганская площадь, 45", "postal_code": "109147"},
        {"title": f"{test_prefix} Отель Москва Тверская 012", "city": "Москва", "address": f"{test_prefix} Тверская улица, 25", "postal_code": "103009"},
        {"title": f"{test_prefix} Отель Москва Парк 013", "city": "Москва", "address": f"{test_prefix} Парковая аллея, 33", "postal_code": "105484"},
    ]
    
    hotel_ids = []
    for hotel in hotels:
        response = client.post("/hotels", json=hotel)
        if response.status_code != 200:
            error_detail = response.json().get("detail", "Unknown error") if response.status_code != 200 else ""
            assert False, f"Не удалось создать отель {hotel['title']}: {response.status_code} - {error_detail}"
        assert response.json() == {"status": "OK"}
    
    response = client.get(
        "/hotels",
        params={
            "title": test_prefix,
            "per_page": 20,
            "page": 1
        }
    )
    assert response.status_code == 200
    hotels_data = response.json()
    
    created_titles = {h["title"] for h in hotels}
    for hotel in hotels_data:
        if hotel["title"] in created_titles:
            hotel_ids.append(hotel["id"])
    
    yield hotel_ids
    
    for hotel_id in hotel_ids:
        client.delete(f"/hotels/{hotel_id}")


@pytest.fixture(scope="session")
def created_room_ids(client, created_hotel_ids, test_prefix):
    """Создает тестовые комнаты и возвращает список их ID"""
    if not created_hotel_ids:
        yield []
        return
    
    hotel_id = created_hotel_ids[0]
    rooms = [
        {"title": f"{test_prefix} Стандартный номер", "description": f"{test_prefix} Уютный номер с видом на город", "price": 3000, "quantity": 5},
        {"title": f"{test_prefix} Люкс", "description": f"{test_prefix} Просторный номер с балконом", "price": 5000, "quantity": 3},
        {"title": f"{test_prefix} Президентский люкс", "description": f"{test_prefix} Роскошный номер", "price": 10000, "quantity": 1},
    ]
    
    room_ids = []
    for room in rooms:
        response = client.post(f"/hotels/{hotel_id}/rooms", json=room)
        assert response.status_code == 200, f"Не удалось создать комнату {room['title']}"
        assert response.json() == {"status": "OK"}
    
    response = client.get(f"/hotels/{hotel_id}/rooms")
    if response.status_code == 200:
        rooms_data = response.json()
        for room in rooms_data:
            if room["title"] in [r["title"] for r in rooms]:
                room_ids.append(room["id"])
    
    yield room_ids
    
    for hotel_id in created_hotel_ids:
        response = client.get(f"/hotels/{hotel_id}/rooms", params={"per_page": 20, "page": 1})
        if response.status_code == 200:
            rooms = response.json()
            for room in rooms:
                if room["id"] in room_ids:
                    client.delete(f"/hotels/{hotel_id}/rooms/{room['id']}")


@pytest.fixture(scope="function")
def created_user_ids():
    """Список ID созданных пользователей для очистки"""
    user_ids = []
    yield user_ids
    
    for user_id in user_ids:
        pass


@pytest.fixture(scope="function")
def created_facility_ids():
    """Список ID созданных удобств для очистки"""
    facility_ids = []
    yield facility_ids
    
    for facility_id in facility_ids:
        pass


@pytest.fixture(scope="function")
def created_image_ids():
    """Список ID созданных изображений для очистки"""
    image_ids = []
    yield image_ids
    
    for image_id in image_ids:
        pass


@pytest.fixture(scope="function")
def created_booking_ids():
    """Список ID созданных бронирований для очистки"""
    booking_ids = []
    yield booking_ids
    
    for booking_id in booking_ids:
        pass


@pytest.fixture(scope="function")
def created_booking_user_map():
    """Словарь: booking_id -> (user_id, user_email) для правильной очистки"""
    booking_map: Dict[int, Tuple[int, str]] = {}
    yield booking_map


@pytest.fixture(scope="function", autouse=True)
def cleanup_after_test(
    client,
    test_prefix,
    created_user_ids,
    created_facility_ids,
    created_image_ids,
    created_booking_ids,
    created_booking_user_map
):
    """Автоматическая очистка после каждого теста"""
    yield
    
    for image_id in created_image_ids[:]:
        try:
            client.delete(f"/images/{image_id}")
        except:
            pass
    
    for facility_id in created_facility_ids[:]:
        try:
            client.delete(f"/facilities/{facility_id}")
        except:
            pass
    
    bookings_by_user = {}
    for booking_id in created_booking_ids:
        if booking_id in created_booking_user_map:
            user_id, user_email = created_booking_user_map[booking_id]
            if user_email not in bookings_by_user:
                bookings_by_user[user_email] = []
            bookings_by_user[user_email].append(booking_id)
    
    for user_email, booking_ids in bookings_by_user.items():
        if user_email:
            try:
                login_response = client.post(
                    "/auth/login",
                    json={
                        "email": user_email,
                        "password": TEST_PASSWORD
                    }
                )
                if login_response.status_code == 200:
                    access_token = login_response.cookies.get("access_token")
                    if access_token:
                        client.headers["Authorization"] = f"Bearer {access_token}"
                    
                    for booking_id in booking_ids:
                        try:
                            client.delete(f"/bookings/{booking_id}")
                        except:
                            pass
                    
                    if "Authorization" in client.headers:
                        del client.headers["Authorization"]
            except:
                pass
    
    for user_id in created_user_ids[:]:
        try:
            client.delete(f"/users/{user_id}")
        except:
            pass

