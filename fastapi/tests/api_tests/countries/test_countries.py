import time

import pytest


def _generate_unique_iso_code(timestamp: int, offset: int = 0) -> str:
    """Генерирует уникальный ISO код из timestamp с опциональным смещением"""
    # Используем разные части timestamp для большей уникальности
    letter1 = chr(ord("A") + (((timestamp + offset) % 100) % 26))
    letter2 = chr(ord("A") + ((((timestamp + offset) // 100) % 100) % 26))
    return f"{letter1}{letter2}"


@pytest.mark.countries
class TestCountries:
    """Эндпоинты стран"""

    def test_get_all_countries(self, client):
        """Получение всех стран"""
        response = client.get("/countries")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_get_country_by_id(self, client, test_prefix):
        """Получение страны по ID"""
        timestamp = int(time.time() * 1000)
        unique_name = f"{test_prefix} Тестовая Страна {timestamp}"
        # Генерируем уникальный ISO код из timestamp
        letter1 = chr(ord("A") + (timestamp % 26))
        letter2 = chr(ord("A") + ((timestamp // 26) % 26))
        unique_iso = f"{letter1}{letter2}"
        country_data = {"name": unique_name, "iso_code": unique_iso}
        create_response = client.post("/countries", json=country_data)
        if create_response.status_code == 200:
            get_response = client.get(f"/countries?name={unique_name}")
            if get_response.status_code == 200 and get_response.json():
                country_id = get_response.json()[0]["id"]

                response = client.get(f"/countries/{country_id}")
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, dict)
                assert "id" in data
                assert "name" in data
                assert "iso_code" in data
                assert data["name"] == unique_name
                assert data["iso_code"] == unique_iso

                client.delete(f"/countries/{country_id}")

    def test_get_country_by_id_nonexistent(self, client):
        """Получение несуществующей страны по ID"""
        response = client.get("/countries/99999")
        assert response.status_code == 404
        assert "не найд" in response.json()["detail"].lower()

    def test_create_country(self, client, test_prefix):
        """Создание страны"""
        timestamp = int(time.time() * 1000)
        unique_name = f"{test_prefix} Новая Страна {timestamp}"
        # Используем функцию для генерации уникального ISO кода
        unique_iso = _generate_unique_iso_code(timestamp)
        country_data = {"name": unique_name, "iso_code": unique_iso}
        response = client.post("/countries", json=country_data)
        # Если получили 409 (конфликт), пробуем с другим ISO кодом
        offset = 1
        while response.status_code == 409 and offset < 10:
            unique_iso = _generate_unique_iso_code(timestamp, offset)
            country_data = {"name": unique_name, "iso_code": unique_iso}
            response = client.post("/countries", json=country_data)
            offset += 1
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}

        get_response = client.get(f"/countries?name={unique_name}")
        if get_response.status_code == 200 and get_response.json():
            country_id = get_response.json()[0]["id"]
            client.delete(f"/countries/{country_id}")

    def test_create_country_duplicate_name(self, client, test_prefix):
        """Создание страны с дублирующимся названием"""
        timestamp = int(time.time() * 1000)
        unique_name = f"{test_prefix} Дубликат {timestamp}"
        # Используем функцию для генерации уникального ISO кода
        unique_iso1 = _generate_unique_iso_code(timestamp)
        country_data = {"name": unique_name, "iso_code": unique_iso1}
        create_response = client.post("/countries", json=country_data)
        # Если получили 409 (конфликт), пробуем с другим ISO кодом
        offset = 1
        while create_response.status_code == 409 and offset < 10:
            unique_iso1 = _generate_unique_iso_code(timestamp, offset)
            country_data = {"name": unique_name, "iso_code": unique_iso1}
            create_response = client.post("/countries", json=country_data)
            offset += 1
        assert create_response.status_code == 200

        # Для второго ISO кода используем другой offset, чтобы гарантировать уникальность
        unique_iso2 = _generate_unique_iso_code(timestamp, offset + 10)
        duplicate_response = client.post("/countries", json={"name": unique_name, "iso_code": unique_iso2})
        assert duplicate_response.status_code == 409
        assert "уже существует" in duplicate_response.json()["detail"]

        get_response = client.get(f"/countries?name={unique_name}")
        if get_response.status_code == 200 and get_response.json():
            country_id = get_response.json()[0]["id"]
            client.delete(f"/countries/{country_id}")

    def test_create_country_duplicate_iso_code(self, client, test_prefix):
        """Создание страны с дублирующимся ISO кодом"""
        timestamp = int(time.time() * 1000)
        unique_name1 = f"{test_prefix} Страна 1 {timestamp}"
        unique_name2 = f"{test_prefix} Страна 2 {timestamp}"
        # Используем функцию для генерации уникального ISO кода
        unique_iso = _generate_unique_iso_code(timestamp)

        create_response = client.post("/countries", json={"name": unique_name1, "iso_code": unique_iso})
        # Если получили 409 (конфликт), пробуем с другим ISO кодом
        offset = 1
        while create_response.status_code == 409 and offset < 10:
            unique_iso = _generate_unique_iso_code(timestamp, offset)
            create_response = client.post("/countries", json={"name": unique_name1, "iso_code": unique_iso})
            offset += 1
        assert create_response.status_code == 200

        # Пытаемся создать страну с тем же ISO кодом, но другим именем
        duplicate_response = client.post("/countries", json={"name": unique_name2, "iso_code": unique_iso})
        assert duplicate_response.status_code == 409
        assert (
            "ISO код" in duplicate_response.json()["detail"] and "уже существует" in duplicate_response.json()["detail"]
        )

        get_response = client.get(f"/countries?name={unique_name1}")
        if get_response.status_code == 200 and get_response.json():
            country_id = get_response.json()[0]["id"]
            client.delete(f"/countries/{country_id}")

    def test_update_country(self, client, test_prefix):
        """Обновление страны"""
        timestamp = int(time.time() * 1000)
        unique_name = f"{test_prefix} Обновляемая {timestamp}"
        # Генерируем уникальный ISO код
        letter1 = chr(ord("A") + (timestamp % 26))
        letter2 = chr(ord("A") + ((timestamp // 26) % 26))
        unique_iso = f"{letter1}{letter2}"
        country_data = {"name": unique_name, "iso_code": unique_iso}
        create_response = client.post("/countries", json=country_data)
        assert create_response.status_code == 200

        get_response = client.get(f"/countries?name={unique_name}")
        if get_response.status_code == 200 and get_response.json():
            country_id = get_response.json()[0]["id"]

            updated_name = f"{test_prefix} Обновленная {timestamp}"
            response = client.put(f"/countries/{country_id}", json={"name": updated_name, "iso_code": unique_iso})
            assert response.status_code == 200
            assert response.json() == {"status": "OK"}

            get_response = client.get(f"/countries/{country_id}")
            assert get_response.status_code == 200
            assert get_response.json()["name"] == updated_name

            client.delete(f"/countries/{country_id}")

    @pytest.mark.parametrize(
        "method,endpoint,json_data",
        [
            ("put", "/countries/99999", {"name": "Тест", "iso_code": "TT"}),
            ("patch", "/countries/99999", {"name": "Test"}),
            ("delete", "/countries/99999", None),
        ],
    )
    def test_country_nonexistent_operations(self, client, method, endpoint, json_data):
        """Операции с несуществующей страной"""
        if json_data is None:
            response = client.delete(endpoint)
        elif method == "put":
            response = client.put(endpoint, json=json_data)
        else:
            response = client.patch(endpoint, json=json_data)

        assert response.status_code == 404

    def test_partial_update_country(self, client, test_prefix):
        """Частичное обновление страны"""
        timestamp = int(time.time() * 1000)
        unique_name = f"{test_prefix} Частично {timestamp}"
        # Генерируем уникальный ISO код с retry логикой на случай коллизий
        unique_iso = _generate_unique_iso_code(timestamp)
        country_data = {"name": unique_name, "iso_code": unique_iso}
        create_response = client.post("/countries", json=country_data)
        # Если получили 409 (конфликт), пробуем с другим ISO кодом
        offset = 1
        while create_response.status_code == 409 and offset < 10:
            unique_iso = _generate_unique_iso_code(timestamp, offset)
            country_data = {"name": unique_name, "iso_code": unique_iso}
            create_response = client.post("/countries", json=country_data)
            offset += 1
        assert create_response.status_code == 200

        get_response = client.get(f"/countries?name={unique_name}")
        if get_response.status_code == 200 and get_response.json():
            country_id = get_response.json()[0]["id"]

            updated_name = f"{test_prefix} Частично Обновленная {timestamp}"
            response = client.patch(f"/countries/{country_id}", json={"name": updated_name})
            assert response.status_code == 200
            assert response.json() == {"status": "OK"}

            get_response = client.get(f"/countries/{country_id}")
            assert get_response.status_code == 200
            assert get_response.json()["name"] == updated_name

            client.delete(f"/countries/{country_id}")

    def test_delete_country(self, client, test_prefix):
        """Удаление страны"""
        timestamp = int(time.time() * 1000)
        unique_name = f"{test_prefix} Для удаления {timestamp}"
        # Генерируем уникальный ISO код
        letter1 = chr(ord("A") + (timestamp % 26))
        letter2 = chr(ord("A") + ((timestamp // 26) % 26))
        unique_iso = f"{letter1}{letter2}"
        country_data = {"name": unique_name, "iso_code": unique_iso}
        create_response = client.post("/countries", json=country_data)
        assert create_response.status_code == 200

        get_response = client.get(f"/countries?name={unique_name}")
        if get_response.status_code == 200 and get_response.json():
            country_id = get_response.json()[0]["id"]

            response = client.delete(f"/countries/{country_id}")
            assert response.status_code == 200
            assert response.json() == {"status": "OK"}

            get_response = client.get(f"/countries/{country_id}")
            assert get_response.status_code == 404

    def test_filter_countries_by_name(self, client, test_prefix):
        """Фильтрация стран по названию"""
        timestamp = int(time.time() * 1000)
        unique_name = f"{test_prefix} Фильтр Тест {timestamp}"
        # Генерируем уникальный ISO код
        letter1 = chr(ord("A") + (timestamp % 26))
        letter2 = chr(ord("A") + ((timestamp // 26) % 26))
        unique_iso = f"{letter1}{letter2}"
        country_data = {"name": unique_name, "iso_code": unique_iso}
        create_response = client.post("/countries", json=country_data)
        assert create_response.status_code == 200

        get_response = client.get(f"/countries?name={test_prefix} Фильтр")
        if get_response.status_code == 200 and get_response.json():
            country_id = get_response.json()[0]["id"]

            response = client.get(f"/countries?name={test_prefix} Фильтр")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 1
            assert any(f"{test_prefix} Фильтр" in c["name"] for c in data)

            client.delete(f"/countries/{country_id}")

    def test_countries_pagination(self, client):
        """Пагинация стран"""
        response = client.get("/countries?page=1&per_page=3")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 3
