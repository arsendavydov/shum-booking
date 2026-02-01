from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import _get_async_session_maker
from src.repositories.bookings import BookingsRepository
from src.repositories.cities import CitiesRepository
from src.repositories.countries import CountriesRepository
from src.repositories.facilities import FacilitiesRepository
from src.repositories.hotels import HotelsRepository
from src.repositories.images import ImagesRepository
from src.repositories.rooms import RoomsRepository
from src.repositories.users import UsersRepository


class DBManager:
    """
    Контекстный менеджер для управления сессиями базы данных.

    Используется для создания и управления асинхронными сессиями SQLAlchemy.
    Автоматически закрывает сессию при выходе из контекста.
    """

    def __init__(self):
        """Инициализация DBManager."""
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        """
        Вход в контекстный менеджер.

        Returns:
            AsyncSession: Асинхронная сессия SQLAlchemy
        """
        session_maker = _get_async_session_maker()
        self.session = session_maker()
        return await self.session.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Выход из контекстного менеджера.

        Автоматически закрывает сессию.
        """
        if self.session:
            await self.session.__aexit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def get_hotels_repository(session: AsyncSession) -> HotelsRepository:
        """
        Получить репозиторий отелей.

        Args:
            session: Сессия базы данных

        Returns:
            HotelsRepository: Репозиторий для работы с отелями
        """
        return HotelsRepository(session)

    @staticmethod
    def get_users_repository(session: AsyncSession) -> UsersRepository:
        """
        Получить репозиторий пользователей.

        Args:
            session: Сессия базы данных

        Returns:
            UsersRepository: Репозиторий для работы с пользователями
        """
        return UsersRepository(session)

    @staticmethod
    def get_rooms_repository(session: AsyncSession) -> RoomsRepository:
        """
        Получить репозиторий комнат.

        Args:
            session: Сессия базы данных

        Returns:
            RoomsRepository: Репозиторий для работы с комнатами
        """
        return RoomsRepository(session)

    @staticmethod
    def get_bookings_repository(session: AsyncSession) -> BookingsRepository:
        """
        Получить репозиторий бронирований.

        Args:
            session: Сессия базы данных

        Returns:
            BookingsRepository: Репозиторий для работы с бронированиями
        """
        return BookingsRepository(session)

    @staticmethod
    def get_countries_repository(session: AsyncSession) -> CountriesRepository:
        """
        Получить репозиторий стран.

        Args:
            session: Сессия базы данных

        Returns:
            CountriesRepository: Репозиторий для работы со странами
        """
        return CountriesRepository(session)

    @staticmethod
    def get_cities_repository(session: AsyncSession) -> CitiesRepository:
        """
        Получить репозиторий городов.

        Args:
            session: Сессия базы данных

        Returns:
            CitiesRepository: Репозиторий для работы с городами
        """
        return CitiesRepository(session)

    @staticmethod
    def get_facilities_repository(session: AsyncSession) -> FacilitiesRepository:
        """
        Получить репозиторий удобств.

        Args:
            session: Сессия базы данных

        Returns:
            FacilitiesRepository: Репозиторий для работы с удобствами
        """
        return FacilitiesRepository(session)

    @staticmethod
    def get_images_repository(session: AsyncSession) -> ImagesRepository:
        """
        Получить репозиторий изображений.

        Args:
            session: Сессия базы данных

        Returns:
            ImagesRepository: Репозиторий для работы с изображениями
        """
        return ImagesRepository(session)

    @staticmethod
    async def commit(session: AsyncSession) -> None:
        """
        Выполнить commit транзакции.

        Args:
            session: Сессия базы данных
        """
        await session.commit()

    @staticmethod
    async def rollback(session: AsyncSession) -> None:
        """
        Выполнить rollback транзакции.

        Args:
            session: Сессия базы данных
        """
        await session.rollback()

    @staticmethod
    @asynccontextmanager
    async def transaction(session: AsyncSession):
        """
        Контекстный менеджер для автоматического управления транзакциями.

        Автоматически выполняет commit при успешном завершении
        и rollback при возникновении исключения.

        Args:
            session: Сессия базы данных

        Yields:
            None

        Example:
            async with DBManager.transaction(db):
                repo = DBManager.get_hotels_repository(db)
                await repo.create(...)
        """
        try:
            yield
            await DBManager.commit(session)
        except Exception:
            await DBManager.rollback(session)
            raise
