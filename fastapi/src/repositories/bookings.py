from typing import List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from src.repositories.base import BaseRepository
from src.repositories.utils import apply_pagination, check_date_overlap
from src.models.bookings import BookingsOrm
from src.models.rooms import RoomsOrm
from src.schemas.bookings import SchemaBooking
from src.repositories.mappers.bookings_mapper import BookingsMapper


class BookingsRepository(BaseRepository[BookingsOrm]):
    """
    Репозиторий для работы с бронированиями.
    
    Наследует базовые CRUD методы и добавляет специфичные методы
    для работы с бронированиями.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория бронирований.
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, BookingsOrm)
    
    def _to_schema(self, orm_obj: BookingsOrm) -> SchemaBooking:
        """
        Преобразовать ORM объект бронирования в Pydantic схему.
        
        Args:
            orm_obj: ORM объект бронирования
            
        Returns:
            Pydantic схема SchemaBooking
        """
        return BookingsMapper.to_schema(orm_obj)
    
    async def has_conflicting_bookings(
        self,
        room_id: int,
        date_from: date,
        date_to: date,
        exclude_booking_id: int | None = None
    ) -> bool:
        """
        Проверить, есть ли конфликтующие бронирования для номера на указанные даты.
        
        Два периода пересекаются, если:
        - date_from нового бронирования < date_to существующего И
        - date_to нового бронирования > date_from существующего
        
        Args:
            room_id: ID номера
            date_from: Дата заезда нового бронирования
            date_to: Дата выезда нового бронирования
            exclude_booking_id: ID бронирования для исключения из проверки (при обновлении)
            
        Returns:
            True если есть конфликтующие бронирования, False иначе
        """
        query = select(self.model).where(
            and_(
                self.model.room_id == room_id,
                self.model.date_from < date_to,
                self.model.date_to > date_from
            )
        )
        
        if exclude_booking_id is not None:
            query = query.where(self.model.id != exclude_booking_id)
        
        result = await self.session.execute(query)
        conflicting_bookings = result.scalars().all()
        
        return len(conflicting_bookings) > 0
    
    async def count_conflicting_bookings(
        self,
        room_id: int,
        date_from: date,
        date_to: date,
        exclude_booking_id: int | None = None
    ) -> int:
        """
        Подсчитать количество конфликтующих бронирований для номера на указанные даты.
        
        Args:
            room_id: ID номера
            date_from: Дата заезда нового бронирования
            date_to: Дата выезда нового бронирования
            exclude_booking_id: ID бронирования для исключения из проверки (при обновлении)
            
        Returns:
            Количество конфликтующих бронирований
        """
        query = select(func.count(self.model.id)).where(
            and_(
                self.model.room_id == room_id,
                self.model.date_from < date_to,
                self.model.date_to > date_from
            )
        )
        
        if exclude_booking_id is not None:
            query = query.where(self.model.id != exclude_booking_id)
        
        result = await self.session.execute(query)
        count = result.scalar_one() or 0
        
        return count
    
    async def is_room_available(
        self,
        room_id: int,
        date_from: date,
        date_to: date,
        exclude_booking_id: int | None = None
    ) -> bool:
        """
        Проверить, доступен ли номер для бронирования на указанные даты.
        
        Проверяет, что количество забронированных номеров меньше общего количества (quantity).
        
        Args:
            room_id: ID номера
            date_from: Дата заезда нового бронирования
            date_to: Дата выезда нового бронирования
            exclude_booking_id: ID бронирования для исключения из проверки (при обновлении)
            
        Returns:
            True если номер доступен (есть свободные места), False иначе
        """
        # Получаем информацию о номере (включая quantity)
        room_query = select(RoomsOrm).where(RoomsOrm.id == room_id)
        room_result = await self.session.execute(room_query)
        room = room_result.scalar_one_or_none()
        
        if room is None:
            return False
        
        # Подсчитываем количество конфликтующих бронирований
        booked_count = await self.count_conflicting_bookings(
            room_id=room_id,
            date_from=date_from,
            date_to=date_to,
            exclude_booking_id=exclude_booking_id
        )
        
        # Проверяем, есть ли свободные номера
        return booked_count < room.quantity
    
    async def create_booking_with_validation(
        self,
        room_id: int,
        user_id: int,
        date_from: date,
        date_to: date
    ) -> SchemaBooking:
        """
        Создать бронирование с полной валидацией.
        
        Выполняет все проверки и создает бронирование:
        - Проверяет существование номера
        - Проверяет корректность дат
        - Проверяет доступность номера (с учетом quantity)
        - Рассчитывает цену
        - Создает бронирование
        
        Args:
            room_id: ID номера
            user_id: ID пользователя
            date_from: Дата заезда
            date_to: Дата выезда
            
        Returns:
            Созданное бронирование (Pydantic схема)
            
        Raises:
            ValueError: Если номер не найден, даты некорректны или номер недоступен
        """
        # Проверяем существование номера
        room_query = select(RoomsOrm).where(RoomsOrm.id == room_id)
        room_result = await self.session.execute(room_query)
        room = room_result.scalar_one_or_none()
        
        if room is None:
            raise ValueError("Номер не найден")
        
        # Проверяем корректность дат
        if date_from >= date_to:
            raise ValueError("Дата заезда должна быть раньше даты выезда")
        
        # Проверяем доступность номера (с учетом quantity)
        is_available = await self.is_room_available(
            room_id=room_id,
            date_from=date_from,
            date_to=date_to
        )
        
        if not is_available:
            raise ValueError("Все номера данного типа уже забронированы на указанные даты")
        
        # Рассчитываем общую цену
        try:
            total_price = BookingsOrm.calculate_total_price(
                room_price_per_night=room.price,
                date_from=date_from,
                date_to=date_to
            )
        except ValueError as e:
            raise ValueError(str(e))
        
        # Создаем бронирование
        booking_data = {
            "room_id": room_id,
            "user_id": user_id,
            "date_from": date_from,
            "date_to": date_to,
            "price": total_price
        }
        
        return await self.create(**booking_data)
    
    async def get_paginated(
        self,
        page: int,
        per_page: int,
        user_id: int | None = None
    ) -> List[SchemaBooking]:
        """
        Получить список бронирований с пагинацией и фильтрацией.
        
        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            user_id: Опциональный фильтр по ID пользователя
            
        Returns:
            Список бронирований (Pydantic схемы)
        """
        query = select(self.model)
        
        # Применяем фильтр по user_id, если указан
        if user_id is not None:
            query = query.where(self.model.user_id == user_id)
        
        # Применяем сортировку и пагинацию
        query = query.order_by(self.model.date_from.desc())
        query = apply_pagination(query, page, per_page)
        
        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())
        
        return [self._to_schema(obj) for obj in orm_objs]

