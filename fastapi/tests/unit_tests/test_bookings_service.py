"""
Unit тесты для BookingsService.

Тестируют бизнес-логику сервиса с моками репозиториев.
"""
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions.domain import DateValidationError, EntityNotFoundError, PermissionError, RoomAvailabilityError
from src.models.bookings import BookingsOrm
from src.models.rooms import RoomsOrm
from src.schemas.bookings import SchemaBooking
from src.services.bookings import BookingsService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Фикстура для создания мока сессии."""
    return AsyncMock()


@pytest.fixture
def bookings_service(mock_session):
    """Фикстура для создания экземпляра BookingsService."""
    return BookingsService(mock_session)


@pytest.fixture
def mock_bookings_repo():
    """Фикстура для создания мока репозитория бронирований."""
    return AsyncMock()


class TestBookingsServiceCreateBooking:
    """Тесты для создания бронирований."""

    @pytest.mark.asyncio
    async def test_create_booking_success(self, bookings_service, mock_bookings_repo):
        """Проверить успешное создание бронирования."""
        room_id = 1
        user_id = 1
        date_from = date.today() + timedelta(days=1)
        date_to = date.today() + timedelta(days=3)

        room = RoomsOrm(id=room_id, hotel_id=1, title="Номер", price=1000, quantity=5)
        from datetime import datetime, UTC

        expected_booking = SchemaBooking(
            id=1,
            room_id=room_id,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            price=2000,
            created_at=datetime.now(UTC),
        )

        async def mock_execute(query):
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = room
            return result_mock

        bookings_service.session.execute = mock_execute
        mock_bookings_repo.is_room_available.return_value = True
        mock_bookings_repo.create.return_value = expected_booking

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            result = await bookings_service.create_booking(room_id, user_id, date_from, date_to)

        assert result == expected_booking
        mock_bookings_repo.is_room_available.assert_called_once_with(room_id=room_id, date_from=date_from, date_to=date_to)
        mock_bookings_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_booking_room_not_found(self, bookings_service, mock_bookings_repo):
        """Проверить, что создание бронирования с несуществующим номером выбрасывает исключение."""
        room_id = 999
        user_id = 1
        date_from = date.today() + timedelta(days=1)
        date_to = date.today() + timedelta(days=3)

        async def mock_execute(query):
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = None
            return result_mock

        bookings_service.session.execute = mock_execute

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await bookings_service.create_booking(room_id, user_id, date_from, date_to)

        assert "Номер" in str(exc_info.value)
        mock_bookings_repo.is_room_available.assert_not_called()
        mock_bookings_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_booking_invalid_dates(self, bookings_service, mock_bookings_repo):
        """Проверить, что создание бронирования с некорректными датами выбрасывает исключение."""
        room_id = 1
        user_id = 1
        date_from = date.today() + timedelta(days=3)
        date_to = date.today() + timedelta(days=1)

        room = RoomsOrm(id=room_id, hotel_id=1, title="Номер", price=1000, quantity=5)

        async def mock_execute(query):
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = room
            return result_mock

        bookings_service.session.execute = mock_execute

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            with pytest.raises(DateValidationError) as exc_info:
                await bookings_service.create_booking(room_id, user_id, date_from, date_to)

        assert "Дата заезда должна быть раньше даты выезда" in str(exc_info.value)
        mock_bookings_repo.is_room_available.assert_not_called()
        mock_bookings_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_booking_zero_length_stay(self, bookings_service, mock_bookings_repo):
        """Проверить, что бронирование с одинаковыми датами заезда и выезда не допускается."""
        room_id = 1
        user_id = 1
        date_from = date.today() + timedelta(days=1)
        date_to = date_from

        room = RoomsOrm(id=room_id, hotel_id=1, title="Номер", price=1000, quantity=5)

        async def mock_execute(query):
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = room
            return result_mock

        bookings_service.session.execute = mock_execute

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            with pytest.raises(DateValidationError) as exc_info:
                await bookings_service.create_booking(room_id, user_id, date_from, date_to)

        assert "Дата заезда должна быть раньше даты выезда" in str(exc_info.value)
        mock_bookings_repo.is_room_available.assert_not_called()
        mock_bookings_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_booking_room_not_available(self, bookings_service, mock_bookings_repo):
        """Проверить, что создание бронирования для недоступного номера выбрасывает исключение."""
        room_id = 1
        user_id = 1
        date_from = date.today() + timedelta(days=1)
        date_to = date.today() + timedelta(days=3)

        room = RoomsOrm(id=room_id, hotel_id=1, title="Номер", price=1000, quantity=5)

        async def mock_execute(query):
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = room
            return result_mock

        bookings_service.session.execute = mock_execute
        mock_bookings_repo.is_room_available.return_value = False

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            with pytest.raises(RoomAvailabilityError) as exc_info:
                await bookings_service.create_booking(room_id, user_id, date_from, date_to)

        assert "Все номера данного типа уже забронированы" in str(exc_info.value)
        mock_bookings_repo.is_room_available.assert_called_once_with(room_id=room_id, date_from=date_from, date_to=date_to)
        mock_bookings_repo.create.assert_not_called()


class TestBookingsServiceDeleteBooking:
    """Тесты для удаления бронирований."""

    @pytest.mark.asyncio
    async def test_delete_booking_success(self, bookings_service, mock_bookings_repo):
        """Проверить успешное удаление бронирования."""
        booking_id = 1
        user_id = 1
        from datetime import datetime, UTC

        booking = SchemaBooking(
            id=booking_id,
            room_id=1,
            user_id=user_id,
            date_from=date.today(),
            date_to=date.today(),
            price=1000,
            created_at=datetime.now(UTC),
        )

        mock_bookings_repo.get_by_id.return_value = booking
        mock_bookings_repo.delete.return_value = True

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            result = await bookings_service.delete_booking(booking_id, user_id)

        assert result is True
        mock_bookings_repo.get_by_id.assert_called_once_with(booking_id)
        mock_bookings_repo.delete.assert_called_once_with(booking_id)

    @pytest.mark.asyncio
    async def test_delete_booking_not_found(self, bookings_service, mock_bookings_repo):
        """Проверить удаление несуществующего бронирования."""
        booking_id = 999
        user_id = 1

        mock_bookings_repo.get_by_id.return_value = None

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            result = await bookings_service.delete_booking(booking_id, user_id)

        assert result is False
        mock_bookings_repo.get_by_id.assert_called_once_with(booking_id)
        mock_bookings_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_booking_permission_denied(self, bookings_service, mock_bookings_repo):
        """Проверить, что удаление чужого бронирования выбрасывает исключение."""
        booking_id = 1
        user_id = 1
        other_user_id = 2
        from datetime import datetime, UTC

        booking = SchemaBooking(
            id=booking_id,
            room_id=1,
            user_id=other_user_id,
            date_from=date.today(),
            date_to=date.today(),
            price=1000,
            created_at=datetime.now(UTC),
        )

        mock_bookings_repo.get_by_id.return_value = booking

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            with pytest.raises(PermissionError) as exc_info:
                await bookings_service.delete_booking(booking_id, user_id)

        assert "Недостаточно прав" in str(exc_info.value)
        mock_bookings_repo.get_by_id.assert_called_once_with(booking_id)
        mock_bookings_repo.delete.assert_not_called()


class TestBookingsServiceGetBookings:
    """Тесты для получения бронирований."""

    @pytest.mark.asyncio
    async def test_get_user_bookings_success(self, bookings_service, mock_bookings_repo):
        """Проверить успешное получение бронирований пользователя."""
        user_id = 1
        page = 1
        per_page = 10
        from datetime import datetime, UTC

        expected_bookings = [
            SchemaBooking(
                id=1,
                room_id=1,
                user_id=user_id,
                date_from=date.today(),
                date_to=date.today(),
                price=1000,
                created_at=datetime.now(UTC),
            )
        ]

        mock_bookings_repo.get_paginated.return_value = expected_bookings

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            result = await bookings_service.get_user_bookings(user_id, page, per_page)

        assert result == expected_bookings
        mock_bookings_repo.get_paginated.assert_called_once_with(page=page, per_page=per_page, user_id=user_id)

    @pytest.mark.asyncio
    async def test_get_all_bookings_success(self, bookings_service, mock_bookings_repo):
        """Проверить успешное получение всех бронирований."""
        page = 1
        per_page = 10
        from datetime import datetime, UTC

        expected_bookings = [
            SchemaBooking(
                id=1,
                room_id=1,
                user_id=1,
                date_from=date.today(),
                date_to=date.today(),
                price=1000,
                created_at=datetime.now(UTC),
            )
        ]

        mock_bookings_repo.get_paginated.return_value = expected_bookings

        with patch("src.utils.db_manager.DBManager.get_bookings_repository", return_value=mock_bookings_repo):
            result = await bookings_service.get_all_bookings(page, per_page)

        assert result == expected_bookings
        mock_bookings_repo.get_paginated.assert_called_once_with(page=page, per_page=per_page)

