import pytest
import time


@pytest.mark.cities
class TestCities:
    """Эндпоинты городов"""
    
    def test_get_all_cities(self, client):
        """Получение всех городов"""
        response = client.get("/cities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
    
    def test_get_city_by_id(self, client, test_prefix):
        """Получение города по ID"""
        # Сначала создаем страну
        country_name = f"{test_prefix} Тестовая Страна {int(time.time())}"
        country_response = client.post("/countries", json={"name": country_name, "iso_code": "TC"})
        if country_response.status_code == 200:
            country_get = client.get(f"/countries?name={country_name}")
            if country_get.status_code == 200 and country_get.json():
                country_id = country_get.json()[0]["id"]
                
                # Создаем город
                unique_name = f"{test_prefix} Тестовый Город {int(time.time())}"
                city_data = {"name": unique_name, "country_id": country_id}
                create_response = client.post("/cities", json=city_data)
                if create_response.status_code == 200:
                    city_get = client.get(f"/cities?name={unique_name}")
                    if city_get.status_code == 200 and city_get.json():
                        city_id = city_get.json()[0]["id"]
                        
                        response = client.get(f"/cities/{city_id}")
                        assert response.status_code == 200
                        data = response.json()
                        assert isinstance(data, dict)
                        assert "id" in data
                        assert "name" in data
                        assert "country_id" in data
                        assert data["name"] == unique_name
                        assert data["country_id"] == country_id
                        
                        client.delete(f"/cities/{city_id}")
                        client.delete(f"/countries/{country_id}")
    
    def test_get_city_by_id_nonexistent(self, client):
        """Получение несуществующего города по ID"""
        response = client.get("/cities/99999")
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"].lower()
    
    def test_create_city(self, client, test_prefix):
        """Создание города"""
        # Сначала создаем страну
        country_name = f"{test_prefix} Страна для города {int(time.time())}"
        country_response = client.post("/countries", json={"name": country_name, "iso_code": "CG"})
        if country_response.status_code == 200:
            country_get = client.get(f"/countries?name={country_name}")
            if country_get.status_code == 200 and country_get.json():
                country_id = country_get.json()[0]["id"]
                
                unique_name = f"{test_prefix} Новый Город {int(time.time())}"
                city_data = {"name": unique_name, "country_id": country_id}
                response = client.post("/cities", json=city_data)
                assert response.status_code == 200
                assert response.json() == {"status": "OK"}
                
                city_get = client.get(f"/cities?name={unique_name}")
                if city_get.status_code == 200 and city_get.json():
                    city_id = city_get.json()[0]["id"]
                    client.delete(f"/cities/{city_id}")
                client.delete(f"/countries/{country_id}")
    
    def test_create_city_nonexistent_country(self, client, test_prefix):
        """Создание города с несуществующей страной"""
        unique_name = f"{test_prefix} Город без страны {int(time.time())}"
        city_data = {"name": unique_name, "country_id": 99999}
        response = client.post("/cities", json=city_data)
        assert response.status_code == 404
        assert "Страна" in response.json()["detail"]
    
    def test_create_city_duplicate(self, client, test_prefix):
        """Создание города с дублирующимся названием в той же стране"""
        # Сначала создаем страну
        country_name = f"{test_prefix} Дубликат Страна {int(time.time())}"
        country_response = client.post("/countries", json={"name": country_name, "iso_code": "DS"})
        if country_response.status_code == 200:
            country_get = client.get(f"/countries?name={country_name}")
            if country_get.status_code == 200 and country_get.json():
                country_id = country_get.json()[0]["id"]
                
                unique_name = f"{test_prefix} Дубликат Город {int(time.time())}"
                city_data = {"name": unique_name, "country_id": country_id}
                create_response = client.post("/cities", json=city_data)
                assert create_response.status_code == 200
                
                duplicate_response = client.post("/cities", json=city_data)
                assert duplicate_response.status_code == 409
                assert "уже существует" in duplicate_response.json()["detail"]
                
                city_get = client.get(f"/cities?name={unique_name}")
                if city_get.status_code == 200 and city_get.json():
                    city_id = city_get.json()[0]["id"]
                    client.delete(f"/cities/{city_id}")
                client.delete(f"/countries/{country_id}")
    
    def test_update_city(self, client, test_prefix):
        """Обновление города"""
        # Сначала создаем страну
        country_name = f"{test_prefix} Обновляемая Страна {int(time.time())}"
        country_response = client.post("/countries", json={"name": country_name, "iso_code": "OS"})
        if country_response.status_code == 200:
            country_get = client.get(f"/countries?name={country_name}")
            if country_get.status_code == 200 and country_get.json():
                country_id = country_get.json()[0]["id"]
                
                unique_name = f"{test_prefix} Обновляемый Город {int(time.time())}"
                city_data = {"name": unique_name, "country_id": country_id}
                create_response = client.post("/cities", json=city_data)
                assert create_response.status_code == 200
                
                city_get = client.get(f"/cities?name={unique_name}")
                if city_get.status_code == 200 and city_get.json():
                    city_id = city_get.json()[0]["id"]
                    
                    updated_name = f"{test_prefix} Обновленный Город {int(time.time())}"
                    response = client.put(
                        f"/cities/{city_id}",
                        json={"name": updated_name, "country_id": country_id}
                    )
                    assert response.status_code == 200
                    assert response.json() == {"status": "OK"}
                    
                    get_response = client.get(f"/cities/{city_id}")
                    assert get_response.status_code == 200
                    assert get_response.json()["name"] == updated_name
                    
                    client.delete(f"/cities/{city_id}")
                client.delete(f"/countries/{country_id}")
    
    def test_update_nonexistent_city(self, client):
        """Обновление несуществующего города"""
        response = client.put(
            "/cities/99999",
            json={"name": "Тест", "country_id": 1}
        )
        assert response.status_code == 404
    
    def test_partial_update_city(self, client, test_prefix):
        """Частичное обновление города"""
        # Сначала создаем страну
        country_name = f"{test_prefix} Частично Страна {int(time.time())}"
        country_response = client.post("/countries", json={"name": country_name, "iso_code": "CS"})
        if country_response.status_code == 200:
            country_get = client.get(f"/countries?name={country_name}")
            if country_get.status_code == 200 and country_get.json():
                country_id = country_get.json()[0]["id"]
                
                unique_name = f"{test_prefix} Частично Город {int(time.time())}"
                city_data = {"name": unique_name, "country_id": country_id}
                create_response = client.post("/cities", json=city_data)
                assert create_response.status_code == 200
                
                city_get = client.get(f"/cities?name={unique_name}")
                if city_get.status_code == 200 and city_get.json():
                    city_id = city_get.json()[0]["id"]
                    
                    updated_name = f"{test_prefix} Частично Обновленный {int(time.time())}"
                    response = client.patch(
                        f"/cities/{city_id}",
                        json={"name": updated_name}
                    )
                    assert response.status_code == 200
                    assert response.json() == {"status": "OK"}
                    
                    get_response = client.get(f"/cities/{city_id}")
                    assert get_response.status_code == 200
                    assert get_response.json()["name"] == updated_name
                    
                    client.delete(f"/cities/{city_id}")
                client.delete(f"/countries/{country_id}")
    
    def test_partial_update_nonexistent_city(self, client):
        """Частичное обновление несуществующего города"""
        response = client.patch(
            "/cities/99999",
            json={"name": "Test"}
        )
        assert response.status_code == 404
    
    def test_delete_city(self, client, test_prefix):
        """Удаление города"""
        # Сначала создаем страну
        country_name = f"{test_prefix} Удаление Страна {int(time.time())}"
        country_response = client.post("/countries", json={"name": country_name, "iso_code": "US"})
        if country_response.status_code == 200:
            country_get = client.get(f"/countries?name={country_name}")
            if country_get.status_code == 200 and country_get.json():
                country_id = country_get.json()[0]["id"]
                
                unique_name = f"{test_prefix} Для удаления {int(time.time())}"
                city_data = {"name": unique_name, "country_id": country_id}
                create_response = client.post("/cities", json=city_data)
                assert create_response.status_code == 200
                
                city_get = client.get(f"/cities?name={unique_name}")
                if city_get.status_code == 200 and city_get.json():
                    city_id = city_get.json()[0]["id"]
                    
                    response = client.delete(f"/cities/{city_id}")
                    assert response.status_code == 200
                    assert response.json() == {"status": "OK"}
                    
                    get_response = client.get(f"/cities/{city_id}")
                    assert get_response.status_code == 404
                    
                client.delete(f"/countries/{country_id}")
    
    def test_delete_nonexistent_city(self, client):
        """Удаление несуществующего города"""
        response = client.delete("/cities/99999")
        assert response.status_code == 404
    
    def test_filter_cities_by_name(self, client, test_prefix):
        """фильтрации городов по названию"""
        # Сначала создаем страну
        country_name = f"{test_prefix} Фильтр Страна {int(time.time())}"
        country_response = client.post("/countries", json={"name": country_name, "iso_code": "FS"})
        if country_response.status_code == 200:
            country_get = client.get(f"/countries?name={country_name}")
            if country_get.status_code == 200 and country_get.json():
                country_id = country_get.json()[0]["id"]
                
                unique_name = f"{test_prefix} Фильтр Тест {int(time.time())}"
                city_data = {"name": unique_name, "country_id": country_id}
                create_response = client.post("/cities", json=city_data)
                assert create_response.status_code == 200
                
                city_get = client.get(f"/cities?name={test_prefix} Фильтр")
                if city_get.status_code == 200 and city_get.json():
                    city_id = city_get.json()[0]["id"]
                    
                    response = client.get(f"/cities?name={test_prefix} Фильтр")
                    assert response.status_code == 200
                    data = response.json()
                    assert isinstance(data, list)
                    assert len(data) >= 1
                    assert any(f"{test_prefix} Фильтр" in c["name"] for c in data)
                    
                    client.delete(f"/cities/{city_id}")
                client.delete(f"/countries/{country_id}")
    
    def test_filter_cities_by_country_id(self, client, test_prefix):
        """фильтрации городов по ID страны"""
        # Сначала создаем страну
        country_name = f"{test_prefix} Фильтр по стране {int(time.time())}"
        country_response = client.post("/countries", json={"name": country_name, "iso_code": "FC"})
        if country_response.status_code == 200:
            country_get = client.get(f"/countries?name={country_name}")
            if country_get.status_code == 200 and country_get.json():
                country_id = country_get.json()[0]["id"]
                
                unique_name = f"{test_prefix} Город в стране {int(time.time())}"
                city_data = {"name": unique_name, "country_id": country_id}
                create_response = client.post("/cities", json=city_data)
                assert create_response.status_code == 200
                
                city_get = client.get(f"/cities?country_id={country_id}")
                if city_get.status_code == 200:
                    data = city_get.json()
                    assert isinstance(data, list)
                    assert len(data) >= 1
                    assert any(c["country_id"] == country_id for c in data)
                    
                    city_by_name = client.get(f"/cities?name={unique_name}")
                    if city_by_name.status_code == 200 and city_by_name.json():
                        city_id = city_by_name.json()[0]["id"]
                        client.delete(f"/cities/{city_id}")
                client.delete(f"/countries/{country_id}")
    
    def test_cities_pagination(self, client):
        """пагинации для городов"""
        response = client.get("/cities?page=1&per_page=3")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 3

