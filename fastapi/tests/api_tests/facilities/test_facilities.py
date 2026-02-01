import time

import pytest


@pytest.mark.facilities
class TestFacilities:
    """Эндпоинты удобств"""

    def test_get_all_facilities(self, client):
        """Получение всех удобств"""
        response = client.get("/facilities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_get_facility_by_id(self, client, test_prefix, created_facility_ids):
        """Получение удобства по ID"""
        facility_data = {"title": f"{test_prefix} Тестовое удобство"}
        create_response = client.post("/facilities", json=facility_data)
        if create_response.status_code == 200:
            get_response = client.get(f"/facilities?title={test_prefix} Тестовое")
            if get_response.status_code == 200 and get_response.json():
                facility_id = get_response.json()[0]["id"]
                created_facility_ids.append(facility_id)

                response = client.get(f"/facilities/{facility_id}")
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, dict)
                assert "id" in data
                assert "title" in data
                assert data["title"] == facility_data["title"]

    def test_get_facility_by_id_nonexistent(self, client):
        """Получение несуществующего удобства по ID"""
        response = client.get("/facilities/99999")
        assert response.status_code == 404
        assert "не найдено" in response.json()["detail"].lower()

    def test_create_facility(self, client, test_prefix, created_facility_ids):
        """Создание удобства"""
        facility_data = {"title": f"{test_prefix} Wi-Fi"}
        response = client.post("/facilities", json=facility_data)
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}

        get_response = client.get(f"/facilities?title={test_prefix} Wi-Fi")
        if get_response.status_code == 200 and get_response.json():
            facility_id = get_response.json()[0]["id"]
            created_facility_ids.append(facility_id)

    def test_delete_facility(self, client, test_prefix):
        """Удаление удобства"""
        facility_data = {"title": f"{test_prefix} Удобство для удаления"}
        create_response = client.post("/facilities", json=facility_data)
        assert create_response.status_code == 200

        get_response = client.get(f"/facilities?title={test_prefix} Удобство для удаления")
        if get_response.status_code == 200 and get_response.json():
            facility_id = get_response.json()[0]["id"]

            response = client.delete(f"/facilities/{facility_id}")
            assert response.status_code == 200
            assert response.json() == {"status": "OK"}

            get_response = client.get(f"/facilities/{facility_id}")
            assert get_response.status_code == 404

    def test_filter_facilities_by_title(self, client, test_prefix, created_facility_ids):
        """Фильтрация удобств по названию"""
        facility_data = {"title": f"{test_prefix} Телевизор"}
        create_response = client.post("/facilities", json=facility_data)
        assert create_response.status_code == 200

        get_response = client.get(f"/facilities?title={test_prefix} Телевизор")
        if get_response.status_code == 200 and get_response.json():
            facility_id = get_response.json()[0]["id"]
            created_facility_ids.append(facility_id)

        response = client.get(f"/facilities?title={test_prefix} Телевизор")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(f"{test_prefix} Телевизор" in f["title"] for f in data)

    def test_facilities_pagination(self, client):
        """Пагинация удобств"""
        response = client.get("/facilities?page=1&per_page=3")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 3

    @pytest.mark.cache
    def test_facilities_cache(self, client, test_prefix, created_facility_ids):
        """Кэширование удобств"""
        unique_title = f"{test_prefix} Кэш проверка {int(time.time())}"
        facility_data = {"title": unique_title}
        create_response = client.post("/facilities", json=facility_data)
        assert create_response.status_code == 200

        get_response = client.get(f"/facilities?title={unique_title}")
        facility_id = None
        if get_response.status_code == 200 and get_response.json():
            facility_id = get_response.json()[0]["id"]
            created_facility_ids.append(facility_id)

        response1 = client.get(f"/facilities?title={unique_title}")
        assert response1.status_code == 200
        data1 = response1.json()
        assert isinstance(data1, list)
        assert len(data1) >= 1
        assert any(f["title"] == unique_title for f in data1)

        response2 = client.get(f"/facilities?title={unique_title}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2 == data1, "Данные должны быть идентичны (из кэша)"

        if facility_id:
            delete_response = client.delete(f"/facilities/{facility_id}")
            assert delete_response.status_code == 200

        response3 = client.get(f"/facilities?title={unique_title}")
        assert response3.status_code == 200
        data3 = response3.json()
        assert not any(f["title"] == unique_title for f in data3), (
            "Удаленное удобство не должно быть в списке (кэш инвалидирован)"
        )

    @pytest.mark.cache
    def test_facilities_cache_invalidation_on_create(self, client, test_prefix, created_facility_ids):
        """Инвалидация кэша при создании"""
        unique_title = f"{test_prefix} Кэш инвалидация создание {int(time.time())}"
        filter_title = f"{test_prefix} Кэш"

        response1 = client.get(f"/facilities?title={filter_title}&page=1&per_page=10")
        assert response1.status_code == 200
        data1 = response1.json()
        assert isinstance(data1, list)
        assert not any(f["title"] == unique_title for f in data1)

        response2 = client.get(f"/facilities?title={filter_title}&page=1&per_page=10")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2 == data1, "Данные должны быть из кэша"

        facility_data = {"title": unique_title}
        create_response = client.post("/facilities", json=facility_data)
        assert create_response.status_code == 200

        get_response = client.get(f"/facilities?title={unique_title}")
        facility_id = None
        if get_response.status_code == 200 and get_response.json():
            facility_id = get_response.json()[0]["id"]
            created_facility_ids.append(facility_id)

        response3 = client.get(f"/facilities?title={filter_title}&page=1&per_page=10")
        assert response3.status_code == 200
        data3 = response3.json()
        assert isinstance(data3, list)
        assert any(f["title"] == unique_title for f in data3), (
            "Новое удобство должно быть доступно после создания (кэш инвалидирован)"
        )

    @pytest.mark.cache
    def test_facilities_cache_invalidation_on_delete(self, client, test_prefix):
        """Инвалидация кэша при удалении"""
        facility_data = {"title": f"{test_prefix} Кэш тест удаление"}
        create_response = client.post("/facilities", json=facility_data)
        assert create_response.status_code == 200

        get_response = client.get(f"/facilities?title={test_prefix} Кэш тест удаление")
        facility_id = None
        if get_response.status_code == 200 and get_response.json():
            facility_id = get_response.json()[0]["id"]

        response1 = client.get("/facilities?page=1&per_page=10")
        assert response1.status_code == 200
        data1 = response1.json()
        assert isinstance(data1, list)

        response2 = client.get("/facilities?page=1&per_page=10")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2 == data1, "Данные должны быть из кэша"

        if facility_id:
            delete_response = client.delete(f"/facilities/{facility_id}")
            assert delete_response.status_code == 200

        response3 = client.get("/facilities?page=1&per_page=10")
        assert response3.status_code == 200
        data3 = response3.json()
        assert isinstance(data3, list)

        if facility_id:
            assert not any(f["id"] == facility_id for f in data3), (
                "Удаленное удобство не должно быть в списке после удаления"
            )
