import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from src.config import settings
from src.schemas.users import UserRegister, UserRequestRegister


class AuthService:
    """
    Сервис для работы с аутентификацией и авторизацией.
    Инкапсулирует логику хеширования паролей, создания/проверки JWT токенов.
    """

    def __init__(self):
        """Инициализация сервиса с настройками из config."""
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        self.cookie_secure = settings.JWT_COOKIE_SECURE

    def hash_password(self, password: str) -> str:
        """
        Хешировать пароль с использованием bcrypt.

        Bcrypt имеет ограничение на длину пароля - максимум 72 байта.
        Пароль автоматически обрезается до 72 байт перед хешированием.

        Args:
            password: Пароль в открытом виде

        Returns:
            Хешированный пароль в формате строки
        """
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверить соответствие пароля хешу.

        Bcrypt имеет ограничение на длину пароля - максимум 72 байта.
        Пароль автоматически обрезается до 72 байт перед проверкой.

        Args:
            plain_password: Пароль в открытом виде
            hashed_password: Хешированный пароль

        Returns:
            True если пароль совпадает, False иначе
        """
        password_bytes = plain_password.encode("utf-8")
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]

        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    def prepare_user_data_for_registration(self, user_data: UserRequestRegister) -> UserRegister:
        """
        Подготовить данные пользователя для регистрации.
        Хеширует пароль и возвращает валидированную Pydantic схему с данными для создания пользователя.

        Args:
            user_data: Данные регистрации пользователя (с паролем в открытом виде)

        Returns:
            UserRegister: Валидированная схема с данными для создания пользователя (с захешированным паролем)
        """
        hashed_password = self.hash_password(user_data.password)

        return UserRegister(
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            telegram_id=user_data.telegram_id,
            pachca_id=user_data.pachca_id,
        )

    def create_access_token(self, data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        """
        Создать JWT access токен.

        Args:
            data: Данные для включения в токен (обычно user_id, email и т.д.)
            expires_delta: Время жизни токена. Если не указано, используется значение из настроек.

        Returns:
            Закодированный JWT токен в виде строки
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=self.expire_minutes)

        to_encode.update({"exp": expire, "iat": datetime.now(UTC)})

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    def decode_access_token(self, token: str) -> dict[str, Any] | None:
        """
        Декодировать и проверить JWT токен.

        Args:
            token: JWT токен в виде строки

        Returns:
            Словарь с данными из токена или None, если токен невалиден/истек
        """
        if not token:
            return None

        # Проверяем базовую структуру JWT токена (должен состоять из 3 частей, разделенных точками)
        parts = token.split(".")
        if len(parts) != 3:
            return None

        try:
            # Явно указываем, что нужно проверять подпись
            # PyJWT должен выбрасывать InvalidTokenError при неверной подписи
            # Используем verify=True по умолчанию (это включено по умолчанию, но явно указываем)
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                },
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            # Включает InvalidSignatureError, DecodeError и другие ошибки валидации
            # InvalidSignatureError является подклассом InvalidTokenError в PyJWT
            return None
        except Exception:
            # Ловим любые другие исключения (например, при поврежденном токене)
            return None

    def generate_refresh_token(self) -> str:
        """
        Сгенерировать случайный refresh токен.

        Returns:
            Случайный токен в виде строки
        """
        return secrets.token_urlsafe(32)

    def get_refresh_token_expires_at(self) -> datetime:
        """
        Получить время истечения refresh токена.

        Returns:
            Время истечения токена
        """
        return datetime.now(UTC) + timedelta(days=self.refresh_token_expire_days)
