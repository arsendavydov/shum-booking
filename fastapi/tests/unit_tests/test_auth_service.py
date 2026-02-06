"""
Unit тесты для AuthService.

Тестируют логику аутентификации без зависимостей от БД и репозиториев.
"""
import time
from datetime import UTC, datetime, timedelta

import pytest

from src.services.auth import AuthService
from src.schemas.users import UserRequestRegister

pytestmark = pytest.mark.unit


@pytest.fixture
def auth_service():
    """Фикстура для создания экземпляра AuthService."""
    return AuthService()


class TestAuthServicePasswordHashing:
    """Тесты для хеширования и проверки паролей."""

    def test_hash_password_returns_string(self, auth_service):
        """Проверить, что hash_password возвращает строку."""
        password = "test_password_123"
        hashed = auth_service.hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_hash_password_different_passwords_different_hashes(self, auth_service):
        """Проверить, что разные пароли дают разные хеши."""
        password1 = "password1"
        password2 = "password2"
        hashed1 = auth_service.hash_password(password1)
        hashed2 = auth_service.hash_password(password2)
        assert hashed1 != hashed2

    def test_hash_password_same_password_different_hashes(self, auth_service):
        """Проверить, что одинаковые пароли дают разные хеши (из-за соли)."""
        password = "same_password"
        hashed1 = auth_service.hash_password(password)
        hashed2 = auth_service.hash_password(password)
        assert hashed1 != hashed2

    def test_verify_password_correct_password(self, auth_service):
        """Проверить, что verify_password возвращает True для правильного пароля."""
        password = "test_password_123"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self, auth_service):
        """Проверить, что verify_password возвращает False для неправильного пароля."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(wrong_password, hashed) is False

    def test_hash_password_long_password_truncated(self, auth_service):
        """Проверить, что длинные пароли (>72 байта) обрезаются."""
        long_password = "a" * 100
        hashed = auth_service.hash_password(long_password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_verify_password_long_password_truncated(self, auth_service):
        """Проверить, что длинные пароли (>72 байта) обрезаются при проверке."""
        long_password = "a" * 100
        hashed = auth_service.hash_password(long_password)
        assert auth_service.verify_password(long_password, hashed) is True


class TestAuthServiceJWT:
    """Тесты для работы с JWT токенами."""

    def test_create_access_token_returns_string(self, auth_service):
        """Проверить, что create_access_token возвращает строку."""
        data = {"sub": "123", "email": "test@example.com"}
        token = auth_service.create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_data(self, auth_service):
        """Проверить, что токен содержит переданные данные."""
        data = {"sub": "123", "email": "test@example.com"}
        token = auth_service.create_access_token(data)
        decoded = auth_service.decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "123"
        assert decoded["email"] == "test@example.com"

    def test_create_access_token_has_expiration(self, auth_service):
        """Проверить, что токен имеет время истечения."""
        data = {"sub": "123"}
        token = auth_service.create_access_token(data)
        decoded = auth_service.decode_access_token(token)
        assert decoded is not None
        assert "exp" in decoded
        assert "iat" in decoded
        assert decoded["exp"] > decoded["iat"]

    def test_create_access_token_custom_expiration(self, auth_service):
        """Проверить, что можно задать кастомное время истечения."""
        data = {"sub": "123"}
        custom_delta = timedelta(minutes=30)
        token = auth_service.create_access_token(data, expires_delta=custom_delta)
        decoded = auth_service.decode_access_token(token)
        assert decoded is not None
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=UTC)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=UTC)
        expected_exp = iat_time + custom_delta
        assert abs((exp_time - expected_exp).total_seconds()) < 5

    def test_decode_access_token_valid_token(self, auth_service):
        """Проверить, что decode_access_token декодирует валидный токен."""
        data = {"sub": "123", "email": "test@example.com"}
        token = auth_service.create_access_token(data)
        decoded = auth_service.decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "123"
        assert decoded["email"] == "test@example.com"

    def test_decode_access_token_invalid_token(self, auth_service):
        """Проверить, что decode_access_token возвращает None для невалидного токена."""
        invalid_token = "invalid.token.here"
        decoded = auth_service.decode_access_token(invalid_token)
        assert decoded is None

    def test_decode_access_token_tampered_token(self, auth_service):
        """Проверить, что decode_access_token возвращает None для подмененного токена."""
        data = {"sub": "123", "email": "test@example.com"}
        token = auth_service.create_access_token(data)
        # Подменяем последний символ токена, чтобы подпись стала невалидной
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        decoded = auth_service.decode_access_token(tampered)
        assert decoded is None

    def test_decode_access_token_expired_token(self, auth_service):
        """Проверить, что decode_access_token возвращает None для истекшего токена."""
        data = {"sub": "123"}
        expired_delta = timedelta(seconds=-1)
        token = auth_service.create_access_token(data, expires_delta=expired_delta)
        time.sleep(2)
        decoded = auth_service.decode_access_token(token)
        assert decoded is None


class TestAuthServiceRefreshToken:
    """Тесты для работы с refresh токенами."""

    def test_generate_refresh_token_returns_string(self, auth_service):
        """Проверить, что generate_refresh_token возвращает строку."""
        token = auth_service.generate_refresh_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_refresh_token_unique_tokens(self, auth_service):
        """Проверить, что generate_refresh_token генерирует уникальные токены."""
        token1 = auth_service.generate_refresh_token()
        token2 = auth_service.generate_refresh_token()
        assert token1 != token2

    def test_get_refresh_token_expires_at_returns_datetime(self, auth_service):
        """Проверить, что get_refresh_token_expires_at возвращает datetime."""
        expires_at = auth_service.get_refresh_token_expires_at()
        assert isinstance(expires_at, datetime)
        assert expires_at.tzinfo == UTC

    def test_get_refresh_token_expires_at_future_date(self, auth_service):
        """Проверить, что get_refresh_token_expires_at возвращает дату в будущем."""
        expires_at = auth_service.get_refresh_token_expires_at()
        now = datetime.now(UTC)
        assert expires_at > now

    def test_get_refresh_token_expires_at_correct_delta(self, auth_service):
        """Проверить, что get_refresh_token_expires_at возвращает правильную дельту."""
        expires_at = auth_service.get_refresh_token_expires_at()
        now = datetime.now(UTC)
        delta = expires_at - now
        expected_days = auth_service.refresh_token_expire_days
        assert abs(delta.days - expected_days) <= 1


class TestAuthServiceUserRegistration:
    """Тесты для подготовки данных регистрации."""

    def test_prepare_user_data_for_registration_hashes_password(self, auth_service):
        """Проверить, что prepare_user_data_for_registration хеширует пароль."""
        user_data = UserRequestRegister(
            email="test@example.com",
            password="plain_password_123",
        )
        prepared = auth_service.prepare_user_data_for_registration(user_data)
        assert prepared.hashed_password != "plain_password_123"
        assert auth_service.verify_password("plain_password_123", prepared.hashed_password) is True

    def test_prepare_user_data_for_registration_preserves_email(self, auth_service):
        """Проверить, что prepare_user_data_for_registration сохраняет email."""
        user_data = UserRequestRegister(
            email="test@example.com",
            password="password123",
        )
        prepared = auth_service.prepare_user_data_for_registration(user_data)
        assert prepared.email == "test@example.com"

    def test_prepare_user_data_for_registration_preserves_optional_fields(self, auth_service):
        """Проверить, что prepare_user_data_for_registration сохраняет опциональные поля."""
        user_data = UserRequestRegister(
            email="test@example.com",
            password="password123",
            first_name="Иван",
            last_name="Иванов",
            telegram_id=123456789,
            pachca_id=123,
        )
        prepared = auth_service.prepare_user_data_for_registration(user_data)
        assert prepared.first_name == "Иван"
        assert prepared.last_name == "Иванов"
        assert prepared.telegram_id == 123456789
        assert prepared.pachca_id == 123

    def test_prepare_user_data_for_registration_handles_none_fields(self, auth_service):
        """Проверить, что prepare_user_data_for_registration обрабатывает None поля."""
        user_data = UserRequestRegister(
            email="test@example.com",
            password="password123",
        )
        prepared = auth_service.prepare_user_data_for_registration(user_data)
        assert prepared.first_name is None
        assert prepared.last_name is None
        assert prepared.telegram_id is None
        assert prepared.pachca_id is None

