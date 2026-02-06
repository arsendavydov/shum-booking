"""
Unit тесты для HotelsService.

Тестируют бизнес-логику сервиса с моками репозиториев.
"""
from datetime import time
from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions.domain import EntityAlreadyExistsError, EntityNotFoundError, ValidationError
from src.schemas.hotels import SchemaHotel
from src.services.hotels import HotelsService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Фикстура для создания мока сессии."""
    return AsyncMock()


@pytest.fixture
def hotels_service(mock_session):
    """Фикстура для создания экземпляра HotelsService."""
    return HotelsService(mock_session)


@pytest.fixture
def mock_hotels_repo():
    """Фикстура для создания мока репозитория отелей."""
    return AsyncMock()


@pytest.fixture
def mock_cities_repo():
    """Фикстура для создания мока репозитория городов."""
    return AsyncMock()


class TestHotelsServiceCreateHotel:
    """Тесты для создания отелей."""

    @pytest.mark.asyncio
    async def test_create_hotel_success(self, hotels_service, mock_hotels_repo, mock_cities_repo):
        """Проверить успешное создание отеля."""
        title = "Гранд Отель"
        city_name = "Москва"
        address = "Тверская улица, 1"
        from src.models.cities import CitiesOrm

        city_orm = CitiesOrm(id=1, name=city_name, country_id=1)
        expected_hotel = SchemaHotel(id=1, title=title, city_id=1, address=address)

        mock_cities_repo.get_by_name_case_insensitive.return_value = city_orm
        mock_hotels_repo.exists_by_title.return_value = False
        mock_hotels_repo.create.return_value = expected_hotel

        with patch("src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo), patch(
            "src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo
        ):
            result = await hotels_service.create_hotel(title, city_name, address)

        assert result == expected_hotel
        mock_cities_repo.get_by_name_case_insensitive.assert_called_once_with(city_name)
        mock_hotels_repo.exists_by_title.assert_called_once_with(title)
        mock_hotels_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_hotel_city_not_found(self, hotels_service, mock_hotels_repo, mock_cities_repo):
        """Проверить, что создание отеля с несуществующим городом выбрасывает исключение."""
        title = "Гранд Отель"
        city_name = "Несуществующий Город"
        address = "Адрес"

        mock_cities_repo.get_by_name_case_insensitive.return_value = None

        with patch("src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo), patch(
            "src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo
        ):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await hotels_service.create_hotel(title, city_name, address)

        assert "Город" in str(exc_info.value)
        mock_cities_repo.get_by_name_case_insensitive.assert_called_once_with(city_name)
        mock_hotels_repo.exists_by_title.assert_not_called()
        mock_hotels_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_hotel_duplicate_title(self, hotels_service, mock_hotels_repo, mock_cities_repo):
        """Проверить, что создание отеля с существующим названием выбрасывает исключение."""
        title = "Гранд Отель"
        city_name = "Москва"
        address = "Адрес"
        from src.models.cities import CitiesOrm

        city_orm = CitiesOrm(id=1, name=city_name, country_id=1)

        mock_cities_repo.get_by_name_case_insensitive.return_value = city_orm
        mock_hotels_repo.exists_by_title.return_value = True

        with patch("src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo), patch(
            "src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo
        ):
            with pytest.raises(EntityAlreadyExistsError) as exc_info:
                await hotels_service.create_hotel(title, city_name, address)

        assert "Отель" in str(exc_info.value)
        assert "название" in str(exc_info.value)
        mock_cities_repo.get_by_name_case_insensitive.assert_called_once_with(city_name)
        mock_hotels_repo.exists_by_title.assert_called_once_with(title)
        mock_hotels_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_hotel_default_times(self, hotels_service, mock_hotels_repo, mock_cities_repo):
        """Проверить, что создание отеля устанавливает дефолтные значения времени."""
        title = "Гранд Отель"
        city_name = "Москва"
        address = "Адрес"
        from src.models.cities import CitiesOrm

        city_orm = CitiesOrm(id=1, name=city_name, country_id=1)
        expected_hotel = SchemaHotel(id=1, title=title, city_id=1, address=address)

        mock_cities_repo.get_by_name_case_insensitive.return_value = city_orm
        mock_hotels_repo.exists_by_title.return_value = False
        mock_hotels_repo.create.return_value = expected_hotel

        with patch("src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo), patch(
            "src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo
        ):
            result = await hotels_service.create_hotel(title, city_name, address)

        assert result == expected_hotel
        call_args = mock_hotels_repo.create.call_args[1]
        assert call_args["check_in_time"] == time(14, 0)
        assert call_args["check_out_time"] == time(12, 0)


class TestHotelsServiceUpdateHotel:
    """Тесты для обновления отелей."""

    @pytest.mark.asyncio
    async def test_update_hotel_success(self, hotels_service, mock_hotels_repo, mock_cities_repo):
        """Проверить успешное обновление отеля."""
        hotel_id = 1
        title = "Новое Название"
        city_name = "Санкт-Петербург"
        address = "Невский проспект, 1"
        existing_hotel = SchemaHotel(id=hotel_id, title="Старое Название", address="Старый адрес")
        updated_hotel = SchemaHotel(id=hotel_id, title=title, address=address)
        from src.models.cities import CitiesOrm

        city_orm = CitiesOrm(id=2, name=city_name, country_id=1)

        mock_hotels_repo.get_by_id.return_value = existing_hotel
        mock_cities_repo.get_by_name_case_insensitive.return_value = city_orm
        mock_hotels_repo.exists_by_title.return_value = False
        mock_hotels_repo.edit.return_value = updated_hotel

        with patch("src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo), patch(
            "src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo
        ):
            result = await hotels_service.update_hotel(hotel_id, title, city_name, address)

        assert result == updated_hotel
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)
        mock_cities_repo.get_by_name_case_insensitive.assert_called_once_with(city_name)
        mock_hotels_repo.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_hotel_not_found(self, hotels_service, mock_hotels_repo, mock_cities_repo):
        """Проверить, что обновление несуществующего отеля выбрасывает исключение."""
        hotel_id = 999
        title = "Новое Название"
        city_name = "Москва"
        address = "Адрес"

        mock_hotels_repo.get_by_id.return_value = None

        with patch("src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo), patch(
            "src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo
        ):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await hotels_service.update_hotel(hotel_id, title, city_name, address)

        assert "Отель" in str(exc_info.value)
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)
        mock_hotels_repo.edit.assert_not_called()


class TestHotelsServicePartialUpdateHotel:
    """Тесты для частичного обновления отелей."""

    @pytest.mark.asyncio
    async def test_partial_update_hotel_title_only(self, hotels_service, mock_hotels_repo, mock_cities_repo):
        """Проверить частичное обновление только названия."""
        hotel_id = 1
        title = "Новое Название"
        existing_hotel = SchemaHotel(id=hotel_id, title="Старое Название", address="Адрес")
        updated_hotel = SchemaHotel(id=hotel_id, title=title, address="Адрес")

        mock_hotels_repo.get_by_id.return_value = existing_hotel
        mock_hotels_repo.exists_by_title.return_value = False
        mock_hotels_repo.edit.return_value = updated_hotel

        with patch("src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo), patch(
            "src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo
        ):
            result = await hotels_service.partial_update_hotel(hotel_id, title=title)

        assert result == updated_hotel
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)
        mock_hotels_repo.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_update_hotel_no_changes(self, hotels_service, mock_hotels_repo, mock_cities_repo):
        """Проверить частичное обновление без изменений."""
        hotel_id = 1
        existing_hotel = SchemaHotel(id=hotel_id, title="Отель", address="Адрес")

        mock_hotels_repo.get_by_id.return_value = existing_hotel

        with patch("src.utils.db_manager.DBManager.get_cities_repository", return_value=mock_cities_repo), patch(
            "src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo
        ):
            result = await hotels_service.partial_update_hotel(hotel_id)

        assert result == existing_hotel
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)
        mock_hotels_repo.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_hotels_with_available_rooms_invalid_dates(self, hotels_service, mock_hotels_repo):
        """Проверить, что запрос отелей с некорректным периодом дат выбрасывает ошибку валидации."""
        from datetime import date, timedelta

        date_from = date.today()
        date_to = date_from  # некорректно: дата начала равна дате окончания

        with pytest.raises(ValidationError) as exc_info:
            await hotels_service.get_hotels_with_available_rooms(
                date_from=date_from, date_to=date_to, page=1, per_page=10
            )

        assert "Дата начала периода должна быть раньше даты окончания" in str(exc_info.value)


class TestHotelsServiceDeleteHotel:
    """Тесты для удаления отелей."""

    @pytest.mark.asyncio
    async def test_delete_hotel_success(self, hotels_service, mock_hotels_repo):
        """Проверить успешное удаление отеля."""
        hotel_id = 1

        mock_hotels_repo.delete.return_value = True

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo):
            result = await hotels_service.delete_hotel(hotel_id)

        assert result is True
        mock_hotels_repo.delete.assert_called_once_with(hotel_id)

    @pytest.mark.asyncio
    async def test_delete_hotel_not_found(self, hotels_service, mock_hotels_repo):
        """Проверить удаление несуществующего отеля."""
        hotel_id = 999

        mock_hotels_repo.delete.return_value = False

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo):
            result = await hotels_service.delete_hotel(hotel_id)

        assert result is False
        mock_hotels_repo.delete.assert_called_once_with(hotel_id)

