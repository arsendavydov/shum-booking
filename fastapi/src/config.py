from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore

# Корень проекта FastAPI (fastapi/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Путь к .env файлу для локальной разработки
# В Docker переменные передаются через environment в docker-compose.yml
# Локально: Shum/.env (на один уровень выше fastapi/)
env_file_path = PROJECT_ROOT.parent / ".env"

# Используем .env файл только если он существует (для локальной разработки)
# В Docker переменные будут браться из os.environ автоматически
env_file = str(env_file_path) if env_file_path.exists() else None


class Settings(BaseSettings):
    DB_HOST: str  # Хост базы данных (в Docker: имя сервиса postgres, локально: localhost)
    DB_PORT: int  # Порт базы данных
    DB_NAME: str  # Название базы данных
    DB_USERNAME: str  # Имя пользователя базы данных
    DB_PASSWORD: str  # Пароль базы данных

    # JWT настройки
    JWT_SECRET_KEY: str  # Секретный ключ для подписи JWT токенов
    JWT_ALGORITHM: str  # Алгоритм подписи JWT
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int  # Время жизни access токена в минутах
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # Время жизни refresh токена в днях (по умолчанию 30 дней)
    JWT_COOKIE_SECURE: bool  # Использовать secure cookie (только HTTPS)

    # Redis настройки
    REDIS_HOST: str  # Хост Redis (в Docker: имя сервиса redis, локально: localhost)
    REDIS_PORT: int  # Порт Redis
    REDIS_DB: int  # Номер базы данных Redis
    REDIS_PASSWORD: str | None = None  # Пароль Redis (опционально)

    # Логирование
    LOG_LEVEL: str = "INFO"  # Уровень логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Rate Limiting настройки
    RATE_LIMIT_ENABLED: bool = True  # Включить rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60  # Количество запросов в минуту для обычных эндпоинтов
    RATE_LIMIT_AUTH_PER_MINUTE: int = (
        5  # Количество запросов в минуту для эндпоинтов аутентификации (защита от brute-force)
    )

    # Метрики в тестах
    ENABLE_METRICS_IN_TESTS: bool = False  # Включить метрики в тестовом режиме (для тестов метрик)

    model_config = SettingsConfigDict(
        env_file=env_file,  # None в Docker (переменные из os.environ), путь к файлу локально
        env_file_encoding="utf-8",
        extra="allow",
        env_ignore_empty=True,
    )


settings = Settings()
