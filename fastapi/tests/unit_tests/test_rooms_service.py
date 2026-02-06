"""
Unit тесты для RoomsService.

Тестируют бизнес-логику сервиса с моками репозиториев.
"""
from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions.domain import EntityNotFoundError, ValidationError
from src.schemas.rooms import SchemaRoom
from src.services.rooms import RoomsService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Фикстура для создания мока сессии."""
    return AsyncMock()


@pytest.fixture
def rooms_service(mock_session):
    """Фикстура для создания экземпляра RoomsService."""
    return RoomsService(mock_session)


@pytest.fixture
def mock_rooms_repo():
    """Фикстура для создания мока репозитория номеров."""
    return AsyncMock()


@pytest.fixture
def mock_hotels_repo():
    """Фикстура для создания мока репозитория отелей."""
    return AsyncMock()


@pytest.fixture
def mock_facilities_repo():
    """Фикстура для создания мока репозитория удобств."""
    return AsyncMock()


class TestRoomsServiceCreateRoom:
    """Тесты для создания номеров."""

    @pytest.mark.asyncio
    async def test_create_room_success(self, rooms_service, mock_rooms_repo, mock_hotels_repo, mock_facilities_repo):
        """Проверить успешное создание номера."""
        hotel_id = 1
        room_data = {"title": "Номер", "price": 1000, "quantity": 5}
        expected_room = SchemaRoom(id=1, hotel_id=hotel_id, title="Номер", price=1000, quantity=5, description=None, facilities=[])

        from src.schemas.hotels import SchemaHotel

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(
            id=hotel_id, title="Отель", city_id=1, address="Адрес", check_in_time=None, check_out_time=None
        )
        mock_rooms_repo.create.return_value = expected_room

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ), patch("src.utils.db_manager.DBManager.get_facilities_repository", return_value=mock_facilities_repo):
            result = await rooms_service.create_room(hotel_id, room_data)

        assert result == expected_room
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)
        assert room_data["hotel_id"] == hotel_id
        mock_rooms_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_room_hotel_not_found(self, rooms_service, mock_rooms_repo, mock_hotels_repo):
        """Проверить, что создание номера с несуществующим отелем выбрасывает исключение."""
        hotel_id = 999
        room_data = {"title": "Номер", "price": 1000}

        mock_hotels_repo.get_by_id.return_value = None

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await rooms_service.create_room(hotel_id, room_data)

        assert "Отель" in str(exc_info.value)
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)
        mock_rooms_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_room_with_facilities(self, rooms_service, mock_rooms_repo, mock_hotels_repo, mock_facilities_repo):
        """Проверить создание номера с удобствами."""
        hotel_id = 1
        room_data = {"title": "Номер", "price": 1000}
        facility_ids = [1, 2]
        expected_room = SchemaRoom(id=1, hotel_id=hotel_id, title="Номер", price=1000, quantity=5, description=None, facilities=[])

        from src.schemas.hotels import SchemaHotel

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(
            id=hotel_id, title="Отель", city_id=1, address="Адрес", check_in_time=None, check_out_time=None
        )
        mock_rooms_repo.create.return_value = expected_room
        from src.schemas.facilities import SchemaFacility

        mock_facilities_repo.get_by_id.return_value = SchemaFacility(id=1, title="WiFi")

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ), patch("src.utils.db_manager.DBManager.get_facilities_repository", return_value=mock_facilities_repo):
            result = await rooms_service.create_room(hotel_id, room_data, facility_ids=facility_ids)

        assert result == expected_room
        assert mock_facilities_repo.get_by_id.call_count == len(facility_ids)
        assert mock_rooms_repo.add_facility.call_count == len(facility_ids)

    @pytest.mark.asyncio
    async def test_create_room_with_missing_facility_raises_error(
        self, rooms_service, mock_rooms_repo, mock_hotels_repo, mock_facilities_repo
    ):
        """Проверить, что создание номера с несуществующим удобством выбрасывает ошибку."""
        hotel_id = 1
        room_data = {"title": "Номер", "price": 1000, "quantity": 5}
        facility_ids = [1, 2]

        from src.schemas.hotels import SchemaHotel
        from src.schemas.facilities import SchemaFacility

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(
            id=hotel_id, title="Отель", city_id=1, address="Адрес", check_in_time=None, check_out_time=None
        )
        mock_rooms_repo.create.return_value = SchemaRoom(
            id=1, hotel_id=hotel_id, title="Номер", price=1000, quantity=5, description=None, facilities=[]
        )
        # Первое удобство существует, второе — нет
        mock_facilities_repo.get_by_id.side_effect = [SchemaFacility(id=1, title="WiFi"), None]

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ), patch("src.utils.db_manager.DBManager.get_facilities_repository", return_value=mock_facilities_repo):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await rooms_service.create_room(hotel_id, room_data, facility_ids=facility_ids)

        assert "Удобство" in str(exc_info.value)


class TestRoomsServiceUpdateRoom:
    """Тесты для обновления номеров."""

    @pytest.mark.asyncio
    async def test_update_room_success(self, rooms_service, mock_rooms_repo, mock_hotels_repo):
        """Проверить успешное обновление номера."""
        hotel_id = 1
        room_id = 1
        room_data = {"title": "Обновленный Номер", "price": 1500}
        existing_room = SchemaRoom(id=room_id, hotel_id=hotel_id, title="Старый Номер", price=1000, quantity=5, description=None, facilities=[])
        updated_room = SchemaRoom(id=room_id, hotel_id=hotel_id, title="Обновленный Номер", price=1500, quantity=5, description=None, facilities=[])

        from src.schemas.hotels import SchemaHotel

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(
            id=hotel_id, title="Отель", city_id=1, address="Адрес", check_in_time=None, check_out_time=None
        )
        mock_rooms_repo.get_by_id.return_value = existing_room
        mock_rooms_repo.edit.return_value = updated_room

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ):
            result = await rooms_service.update_room(hotel_id, room_id, room_data)

        assert result == updated_room
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)
        mock_rooms_repo.get_by_id.assert_called_once_with(room_id)
        mock_rooms_repo.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_room_wrong_hotel(self, rooms_service, mock_rooms_repo, mock_hotels_repo):
        """Проверить, что обновление номера из другого отеля выбрасывает исключение."""
        hotel_id = 1
        room_id = 1
        wrong_hotel_id = 2
        room_data = {"title": "Номер"}
        existing_room = SchemaRoom(
            id=room_id,
            hotel_id=wrong_hotel_id,
            title="Номер",
            price=1000,
            quantity=5,
            description=None,
            facilities=[],
        )

        from src.schemas.hotels import SchemaHotel

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(
            id=hotel_id, title="Отель", city_id=1, address="Адрес", check_in_time=None, check_out_time=None
        )
        mock_rooms_repo.get_by_id.return_value = existing_room

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ):
            with pytest.raises(ValidationError) as exc_info:
                await rooms_service.update_room(hotel_id, room_id, room_data)

        assert "Номер не принадлежит указанному отелю" in str(exc_info.value)
        mock_rooms_repo.edit.assert_not_called()


class TestRoomsServicePartialUpdateRoom:
    """Тесты для частичного обновления номеров."""

    @pytest.mark.asyncio
    async def test_partial_update_room_success(self, rooms_service, mock_rooms_repo, mock_hotels_repo):
        """Проверить успешное частичное обновление номера."""
        hotel_id = 1
        room_id = 1
        room_data = {"price": 1500}
        existing_room = SchemaRoom(id=room_id, hotel_id=hotel_id, title="Номер", price=1000, quantity=5, description=None, facilities=[])
        updated_room = SchemaRoom(id=room_id, hotel_id=hotel_id, title="Номер", price=1500, quantity=5, description=None, facilities=[])

        from src.schemas.hotels import SchemaHotel

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(
            id=hotel_id, title="Отель", city_id=1, address="Адрес", check_in_time=None, check_out_time=None
        )
        mock_rooms_repo.get_by_id.return_value = existing_room
        mock_rooms_repo.edit.return_value = updated_room

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ):
            result = await rooms_service.partial_update_room(hotel_id, room_id, room_data)

        assert result == updated_room
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)
        mock_rooms_repo.get_by_id.assert_called_once_with(room_id)
        mock_rooms_repo.edit.assert_called_once()


class TestRoomsServiceDeleteRoom:
    """Тесты для удаления номеров."""

    @pytest.mark.asyncio
    async def test_delete_room_success(self, rooms_service, mock_rooms_repo, mock_hotels_repo):
        """Проверить успешное удаление номера."""
        hotel_id = 1
        room_id = 1
        existing_room = SchemaRoom(id=room_id, hotel_id=hotel_id, title="Номер", price=1000, quantity=5, description=None, facilities=[])

        from src.schemas.hotels import SchemaHotel

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(
            id=hotel_id, title="Отель", city_id=1, address="Адрес", check_in_time=None, check_out_time=None
        )
        mock_rooms_repo.get_by_id.return_value = existing_room
        mock_rooms_repo.delete.return_value = True

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ):
            result = await rooms_service.delete_room(hotel_id, room_id)

        assert result is True
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)
        mock_rooms_repo.get_by_id.assert_called_once_with(room_id)
        mock_rooms_repo.delete.assert_called_once_with(room_id)

    @pytest.mark.asyncio
    async def test_delete_room_not_found(self, rooms_service, mock_rooms_repo, mock_hotels_repo):
        """Проверить удаление несуществующего номера."""
        hotel_id = 1
        room_id = 999

        from src.schemas.hotels import SchemaHotel

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(
            id=hotel_id, title="Отель", city_id=1, address="Адрес", check_in_time=None, check_out_time=None
        )
        mock_rooms_repo.get_by_id.return_value = None

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ):
            result = await rooms_service.delete_room(hotel_id, room_id)

        assert result is False
        mock_rooms_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_room_wrong_hotel(self, rooms_service, mock_rooms_repo, mock_hotels_repo):
        """Проверить, что удаление номера из другого отеля выбрасывает исключение."""
        hotel_id = 1
        room_id = 1
        wrong_hotel_id = 2
        existing_room = SchemaRoom(
            id=room_id,
            hotel_id=wrong_hotel_id,
            title="Номер",
            price=1000,
            quantity=5,
            description=None,
            facilities=[],
        )

        from src.schemas.hotels import SchemaHotel

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(
            id=hotel_id, title="Отель", city_id=1, address="Адрес", check_in_time=None, check_out_time=None
        )
        mock_rooms_repo.get_by_id.return_value = existing_room

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo), patch(
            "src.utils.db_manager.DBManager.get_rooms_repository", return_value=mock_rooms_repo
        ):
            with pytest.raises(ValidationError) as exc_info:
                await rooms_service.delete_room(hotel_id, room_id)

        assert "Номер не принадлежит указанному отелю" in str(exc_info.value)
        mock_rooms_repo.delete.assert_not_called()

