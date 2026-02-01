from redis.asyncio import Redis

from src.config import settings


class RedisManager:
    """Менеджер для работы с асинхронным подключением к Redis."""

    _client: Redis | None = None

    def __init__(self, host: str = None, port: int = None, db: int = None, password: str = None):
        """Инициализация RedisManager с параметрами подключения."""
        self.host = host or settings.REDIS_HOST
        self.port = port or settings.REDIS_PORT
        self.db = db or settings.REDIS_DB
        self.password = password or getattr(settings, "REDIS_PASSWORD", None)

    async def connect(self) -> Redis:
        """Создание и возврат асинхронного клиента Redis."""
        if self._client is None:
            self._client = Redis(
                host=self.host, port=self.port, db=self.db, password=self.password, decode_responses=True
            )
        return self._client

    async def check_connection(self) -> bool:
        """Проверка работоспособности подключения к Redis."""
        client = await self.connect()
        return await client.ping()

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """Записать значение по ключу в Redis."""
        client = await self.connect()
        return await client.set(key, value, ex=ex)

    async def get(self, key: str) -> str | None:
        """Получить значение по ключу из Redis."""
        client = await self.connect()
        return await client.get(key)

    async def delete(self, key: str) -> int:
        """Удалить значение по ключу из Redis."""
        client = await self.connect()
        return await client.delete(key)

    async def keys(self, pattern: str) -> list[str]:
        """Получить список ключей по паттерну."""
        client = await self.connect()
        return await client.keys(pattern)

    async def close(self) -> None:
        """Закрытие подключения к Redis."""
        if self._client:
            await self._client.close()
            self._client = None
