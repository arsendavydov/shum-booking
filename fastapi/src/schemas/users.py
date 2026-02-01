from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRequestRegister(BaseModel):
    """Схема запроса на регистрацию пользователя."""

    email: EmailStr = Field(..., max_length=255, description="Email пользователя (обязательно)")
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Пароль пользователя (обязательно, минимум 8 символов, максимум 72 символа из-за ограничений bcrypt)",
    )
    first_name: str | None = Field(None, max_length=100, description="Имя пользователя (опционально)")
    last_name: str | None = Field(None, max_length=100, description="Фамилия пользователя (опционально)")
    telegram_id: int | None = Field(None, description="Telegram ID пользователя (опционально, 64-битное целое число)")
    pachca_id: int | None = Field(None, description="Pachca ID пользователя (опционально, целое число)")


class UserRegister(BaseModel):
    """Схема для создания пользователя в БД."""

    email: EmailStr = Field(..., max_length=255, description="Email пользователя")
    hashed_password: str | None = Field(None, max_length=255, description="Хешированный пароль")
    first_name: str | None = Field(None, max_length=100, description="Имя пользователя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия пользователя")
    telegram_id: int | None = Field(None, description="Telegram ID пользователя (64-битное целое число)")
    pachca_id: int | None = Field(None, description="Pachca ID пользователя (целое число)")


class UserResponse(BaseModel):
    """Схема ответа с ID пользователя (без пароля)."""

    id: int = Field(..., description="ID пользователя")
    email: EmailStr = Field(..., max_length=255, description="Email пользователя")
    first_name: str | None = Field(None, max_length=100, description="Имя пользователя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия пользователя")
    telegram_id: int | None = Field(None, description="Telegram ID пользователя (64-битное целое число)")
    pachca_id: int | None = Field(None, description="Pachca ID пользователя (целое число)")
    model_config = ConfigDict(from_attributes=True)


class UserPATCH(BaseModel):
    """Модель для частичного обновления пользователя."""

    email: EmailStr | None = Field(None, max_length=255, description="Email пользователя (опционально)")
    hashed_password: str | None = Field(None, max_length=255, description="Хешированный пароль (опционально)")
    first_name: str | None = Field(None, max_length=100, description="Имя пользователя (опционально)")
    last_name: str | None = Field(None, max_length=100, description="Фамилия пользователя (опционально)")
    telegram_id: int | None = Field(None, description="Telegram ID пользователя (опционально, 64-битное целое число)")
    pachca_id: int | None = Field(None, description="Pachca ID пользователя (опционально, целое число)")


class SchemaUser(BaseModel):
    """Модель ответа для GET запросов (без пароля)."""

    id: int = Field(..., description="ID пользователя")
    email: EmailStr = Field(..., max_length=255, description="Email пользователя")
    first_name: str | None = Field(None, max_length=100, description="Имя пользователя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия пользователя")
    telegram_id: int | None = Field(None, description="Telegram ID пользователя (64-битное целое число)")
    pachca_id: int | None = Field(None, description="Pachca ID пользователя (целое число)")
    model_config = ConfigDict(from_attributes=True)


class UserRequestLogin(BaseModel):
    """Схема запроса на вход пользователя."""

    email: EmailStr = Field(..., max_length=255, description="Email пользователя")
    password: str = Field(..., min_length=8, max_length=72, description="Пароль пользователя")


class TokenResponse(BaseModel):
    """Схема ответа с JWT токеном."""

    access_token: str = Field(..., description="JWT access токен")
    token_type: str = Field(default="bearer", description="Тип токена")
