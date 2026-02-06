"""
Unit тесты для UsersService.

Тестируют бизнес-логику сервиса с моками репозиториев.
"""
from unittest.mock import AsyncMock, patch

import pytest

from src.exceptions.domain import EntityAlreadyExistsError, EntityNotFoundError
from src.schemas.users import SchemaUser, UserRegister
from src.services.users import UsersService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Фикстура для создания мока сессии."""
    return AsyncMock()


@pytest.fixture
def users_service(mock_session):
    """Фикстура для создания экземпляра UsersService."""
    return UsersService(mock_session)


@pytest.fixture
def mock_users_repo():
    """Фикстура для создания мока репозитория пользователей."""
    return AsyncMock()


class TestUsersServiceRegisterUser:
    """Тесты для регистрации пользователей."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, users_service, mock_users_repo, mock_session):
        """Проверить успешную регистрацию пользователя."""
        user_data = UserRegister(
            email="test@example.com",
            hashed_password="hashed_password_123",
        )
        expected_user = SchemaUser(
            id=1,
            email="test@example.com",
            hashed_password="hashed_password_123",
        )

        mock_users_repo.exists_by_email.return_value = False
        mock_users_repo.create.return_value = expected_user

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            result = await users_service.register_user(user_data)

        assert result == expected_user
        mock_users_repo.exists_by_email.assert_called_once_with("test@example.com")
        mock_users_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, users_service, mock_users_repo):
        """Проверить, что регистрация с существующим email выбрасывает исключение."""
        user_data = UserRegister(
            email="existing@example.com",
            hashed_password="hashed_password_123",
        )

        mock_users_repo.exists_by_email.return_value = True

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            with pytest.raises(EntityAlreadyExistsError) as exc_info:
                await users_service.register_user(user_data)

        assert "Пользователь" in str(exc_info.value)
        assert "email" in str(exc_info.value)
        assert "existing@example.com" in str(exc_info.value)
        mock_users_repo.exists_by_email.assert_called_once_with("existing@example.com")
        mock_users_repo.create.assert_not_called()


class TestUsersServiceUpdateUser:
    """Тесты для обновления пользователей."""

    @pytest.mark.asyncio
    async def test_update_user_success(self, users_service, mock_users_repo):
        """Проверить успешное обновление пользователя."""
        user_id = 1
        user_data = UserRegister(
            email="newemail@example.com",
            hashed_password="new_hashed_password",
        )
        existing_user = SchemaUser(
            id=user_id,
            email="old@example.com",
            hashed_password="old_hashed_password",
        )
        updated_user = SchemaUser(
            id=user_id,
            email="newemail@example.com",
            hashed_password="new_hashed_password",
        )

        mock_users_repo.get_by_id.return_value = existing_user
        mock_users_repo.exists_by_email.return_value = False
        mock_users_repo.edit.return_value = updated_user

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            result = await users_service.update_user(user_id, user_data)

        assert result == updated_user
        mock_users_repo.get_by_id.assert_called_once_with(user_id)
        mock_users_repo.exists_by_email.assert_called_once_with("newemail@example.com")
        mock_users_repo.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, users_service, mock_users_repo):
        """Проверить, что обновление несуществующего пользователя выбрасывает исключение."""
        user_id = 999
        user_data = UserRegister(
            email="test@example.com",
            hashed_password="hashed_password",
        )

        mock_users_repo.get_by_id.return_value = None

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await users_service.update_user(user_id, user_data)

        assert "Пользователь" in str(exc_info.value)
        mock_users_repo.get_by_id.assert_called_once_with(user_id)
        mock_users_repo.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(self, users_service, mock_users_repo):
        """Проверить, что обновление с существующим email выбрасывает исключение."""
        user_id = 1
        user_data = UserRegister(
            email="existing@example.com",
            hashed_password="hashed_password",
        )
        existing_user = SchemaUser(
            id=user_id,
            email="old@example.com",
            hashed_password="old_hashed_password",
        )

        mock_users_repo.get_by_id.return_value = existing_user
        mock_users_repo.exists_by_email.return_value = True

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            with pytest.raises(EntityAlreadyExistsError) as exc_info:
                await users_service.update_user(user_id, user_data)

        assert "Пользователь" in str(exc_info.value)
        assert "email" in str(exc_info.value)
        mock_users_repo.get_by_id.assert_called_once_with(user_id)
        mock_users_repo.exists_by_email.assert_called_once_with("existing@example.com")
        mock_users_repo.edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_same_email_no_check(self, users_service, mock_users_repo):
        """Проверить, что обновление с тем же email не проверяет уникальность."""
        user_id = 1
        user_data = UserRegister(
            email="same@example.com",
            hashed_password="new_hashed_password",
        )
        existing_user = SchemaUser(
            id=user_id,
            email="same@example.com",
            hashed_password="old_hashed_password",
        )
        updated_user = SchemaUser(
            id=user_id,
            email="same@example.com",
            hashed_password="new_hashed_password",
        )

        mock_users_repo.get_by_id.return_value = existing_user
        mock_users_repo.edit.return_value = updated_user

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            result = await users_service.update_user(user_id, user_data)

        assert result == updated_user
        mock_users_repo.get_by_id.assert_called_once_with(user_id)
        mock_users_repo.exists_by_email.assert_not_called()
        mock_users_repo.edit.assert_called_once()


class TestUsersServicePartialUpdateUser:
    """Тесты для частичного обновления пользователей."""

    @pytest.mark.asyncio
    async def test_partial_update_user_success(self, users_service, mock_users_repo):
        """Проверить успешное частичное обновление пользователя."""
        user_id = 1
        update_data = {"first_name": "Новое Имя"}
        existing_user = SchemaUser(
            id=user_id,
            email="test@example.com",
            hashed_password="hashed_password",
            first_name="Старое Имя",
        )
        updated_user = SchemaUser(
            id=user_id,
            email="test@example.com",
            hashed_password="hashed_password",
            first_name="Новое Имя",
        )

        mock_users_repo.get_by_id.return_value = existing_user
        mock_users_repo.update.return_value = updated_user

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            result = await users_service.partial_update_user(user_id, update_data)

        assert result == updated_user
        mock_users_repo.get_by_id.assert_called_once_with(user_id)
        mock_users_repo.update.assert_called_once_with(id=user_id, **update_data)

    @pytest.mark.asyncio
    async def test_partial_update_user_not_found(self, users_service, mock_users_repo):
        """Проверить, что частичное обновление несуществующего пользователя выбрасывает исключение."""
        user_id = 999
        update_data = {"first_name": "Новое Имя"}

        mock_users_repo.get_by_id.return_value = None

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await users_service.partial_update_user(user_id, update_data)

        assert "Пользователь" in str(exc_info.value)
        mock_users_repo.get_by_id.assert_called_once_with(user_id)
        mock_users_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_update_user_duplicate_email(self, users_service, mock_users_repo):
        """Проверить, что частичное обновление с существующим email выбрасывает исключение."""
        user_id = 1
        update_data = {"email": "existing@example.com"}
        existing_user = SchemaUser(
            id=user_id,
            email="old@example.com",
            hashed_password="hashed_password",
        )

        mock_users_repo.get_by_id.return_value = existing_user
        mock_users_repo.exists_by_email.return_value = True

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            with pytest.raises(EntityAlreadyExistsError) as exc_info:
                await users_service.partial_update_user(user_id, update_data)

        assert "Пользователь" in str(exc_info.value)
        assert "email" in str(exc_info.value)
        mock_users_repo.get_by_id.assert_called_once_with(user_id)
        mock_users_repo.exists_by_email.assert_called_once_with("existing@example.com")
        mock_users_repo.update.assert_not_called()


class TestUsersServiceDeleteUser:
    """Тесты для удаления пользователей."""

    @pytest.mark.asyncio
    async def test_delete_user_success(self, users_service, mock_users_repo):
        """Проверить успешное удаление пользователя."""
        user_id = 1

        mock_users_repo.delete.return_value = True

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            result = await users_service.delete_user(user_id)

        assert result is True
        mock_users_repo.delete.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, users_service, mock_users_repo):
        """Проверить удаление несуществующего пользователя."""
        user_id = 999

        mock_users_repo.delete.return_value = False

        with patch("src.utils.db_manager.DBManager.get_users_repository", return_value=mock_users_repo):
            result = await users_service.delete_user(user_id)

        assert result is False
        mock_users_repo.delete.assert_called_once_with(user_id)
