from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.bookings import BookingsOrm
from src.models.rooms import RoomsOrm
from src.repositories.base import BaseRepository
from src.repositories.mappers.rooms_mapper import RoomsMapper
from src.repositories.utils import apply_pagination, apply_text_filter
from src.schemas.rooms import SchemaRoom, SchemaRoomAvailable


class RoomsRepository(BaseRepository[RoomsOrm]):
    """
    Репозиторий для работы с комнатами.

    Наследует базовые CRUD методы и добавляет специфичные методы
    для работы с комнатами.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория комнат.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, RoomsOrm)

    def _to_schema(self, orm_obj: RoomsOrm) -> SchemaRoom:
        """
        Преобразовать ORM объект комнаты в Pydantic схему.

        Args:
            orm_obj: ORM объект комнаты

        Returns:
            Pydantic схема SchemaRoom
        """
        return RoomsMapper.to_schema(orm_obj)

    async def create(self, **kwargs) -> SchemaRoom:
        """
        Создать новую комнату с загрузкой facilities.

        Args:
            **kwargs: Поля для создания комнаты

        Returns:
            Созданная Pydantic схема SchemaRoom
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)

        # Загружаем facilities через selectinload
        query = self._load_room_with_facilities_query(room_id=instance.id)
        result = await self.session.execute(query)
        instance_with_facilities = result.scalar_one()

        return self._to_schema(instance_with_facilities)

    async def edit(self, id: int, **kwargs) -> SchemaRoom | None:
        """
        Изменить комнату по ID с загрузкой facilities.

        Args:
            id: ID комнаты для изменения
            **kwargs: Поля для обновления

        Returns:
            Измененная Pydantic схема SchemaRoom или None, если не найдено
        """
        instance = await self._get_one_by_id_exact(id)

        if instance is None:
            return None

        for key, value in kwargs.items():
            setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)

        # Загружаем facilities через selectinload
        query = self._load_room_with_facilities_query(room_id=id)
        result = await self.session.execute(query)
        instance_with_facilities = result.scalar_one_or_none()

        if instance_with_facilities is None:
            return None

        return self._to_schema(instance_with_facilities)

    async def get_by_id(self, id: int) -> SchemaRoom | None:
        """
        Получить комнату по ID с загрузкой facilities.

        Args:
            id: ID комнаты

        Returns:
            Pydantic схема SchemaRoom или None, если не найдено
        """
        query = self._load_room_with_facilities_query(room_id=id)
        result = await self.session.execute(query)
        orm_obj = result.scalar_one_or_none()

        if orm_obj is None:
            return None

        return self._to_schema(orm_obj)

    async def get_paginated(
        self, page: int, per_page: int, hotel_id: int | None = None, title: str | None = None
    ) -> list[SchemaRoom]:
        """
        Получить список комнат с пагинацией и фильтрацией.

        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            hotel_id: Опциональный фильтр по ID отеля
            title: Опциональный фильтр по названию (частичное совпадение, без учета регистра)

        Returns:
            Список комнат (Pydantic схемы)
        """
        query = self._load_room_with_facilities_query()

        # Применяем фильтры
        if hotel_id is not None:
            query = query.where(self.model.hotel_id == hotel_id)
        if title is not None:
            query = apply_text_filter(query, self.model.title, title)

        # Применяем пагинацию
        query = apply_pagination(query, page, per_page)

        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())

        return [self._to_schema(obj) for obj in orm_objs]

    async def get_by_hotel_id(self, hotel_id: int) -> list[SchemaRoom]:
        """
        Получить комнаты по ID отеля.

        Args:
            hotel_id: ID отеля

        Returns:
            Список комнат (Pydantic схемы)
        """
        query = self._load_room_with_facilities_query().where(self.model.hotel_id == hotel_id)
        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())
        return [self._to_schema(obj) for obj in orm_objs]

    async def count(self, hotel_id: int | None = None, title: str | None = None) -> int:
        """
        Подсчитать количество комнат с учетом фильтров.

        Args:
            hotel_id: Опциональный фильтр по ID отеля
            title: Опциональный фильтр по названию

        Returns:
            Количество комнат
        """
        query = select(func.count(self.model.id))

        if hotel_id is not None:
            query = query.where(self.model.hotel_id == hotel_id)
        if title is not None:
            query = apply_text_filter(query, self.model.title, title)

        result = await self.session.execute(query)
        return result.scalar_one() or 0

    def _load_room_with_facilities_query(self, room_id: int | None = None):
        """
        Создать запрос для загрузки комнаты(комнат) с facilities через selectinload.

        Args:
            room_id: Опциональный ID комнаты. Если указан, загружается только эта комната.

        Returns:
            SQLAlchemy запрос с selectinload для facilities
        """
        query = select(self.model).options(selectinload(self.model.facilities))
        if room_id is not None:
            query = query.where(self.model.id == room_id)
        return query

    async def get_rooms_with_availability(
        self, hotel_id: int, date_from: date, date_to: date
    ) -> list[SchemaRoomAvailable]:
        """
        Получить номера отеля с актуальным количеством свободных номеров на указанный период.

        Для каждого номера вычисляется количество свободных номеров:
        quantity (общее количество) - количество забронированных на указанный период.
        Возвращает только номера с количеством свободных номеров больше 0.

        Args:
            hotel_id: ID отеля
            date_from: Дата начала периода
            date_to: Дата окончания периода

        Returns:
            Список номеров с количеством свободных номеров (quantity > 0)
        """
        # Получаем все номера отеля с загрузкой удобств
        rooms_query = self._load_room_with_facilities_query().where(self.model.hotel_id == hotel_id)
        rooms_result = await self.session.execute(rooms_query)
        rooms = list(rooms_result.scalars().all())

        if not rooms:
            return []

        # Для каждого номера считаем количество забронированных на указанный период
        available_rooms = []
        for room in rooms:
            # Находим все бронирования этого номера, которые пересекаются с указанным периодом
            bookings_query = select(func.count(BookingsOrm.id)).where(
                and_(BookingsOrm.room_id == room.id, BookingsOrm.date_from < date_to, BookingsOrm.date_to > date_from)
            )
            bookings_result = await self.session.execute(bookings_query)
            booked_count = bookings_result.scalar_one() or 0

            # Вычисляем количество свободных номеров
            available_quantity = max(0, room.quantity - booked_count)

            # Добавляем только номера с доступными местами (quantity > 0)
            if available_quantity > 0:
                # Используем маппер для преобразования
                available_room = RoomsMapper.to_schema_available(room, available_quantity)
                available_rooms.append(available_room)

        return available_rooms

    async def get_orm_by_id(self, room_id: int) -> RoomsOrm | None:
        """
        Получить ORM объект комнаты по ID.

        Args:
            room_id: ID комнаты

        Returns:
            ORM объект комнаты или None, если не найдено
        """
        query = select(self.model).where(self.model.id == room_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_facility(self, room_id: int, facility_id: int) -> bool:
        """
        Добавить удобство к комнате.

        Args:
            room_id: ID комнаты
            facility_id: ID удобства

        Returns:
            True если связь создана, False если уже существует

        Raises:
            ValueError: Если комната или удобство не найдены
        """
        from src.models.facilities import FacilitiesOrm, rooms_facilities

        # Проверяем существование комнаты
        room = await self.get_orm_by_id(room_id)
        if room is None:
            raise ValueError("Комната не найдена")

        # Проверяем существование удобства
        facility_query = select(FacilitiesOrm).where(FacilitiesOrm.id == facility_id)
        facility_result = await self.session.execute(facility_query)
        facility = facility_result.scalar_one_or_none()
        if facility is None:
            raise ValueError("Удобство не найдено")

        # Проверяем, существует ли уже связь
        check_query = select(rooms_facilities).where(
            and_(rooms_facilities.c.room_id == room_id, rooms_facilities.c.facility_id == facility_id)
        )
        check_result = await self.session.execute(check_query)
        if check_result.fetchone() is not None:
            return False  # Связь уже существует

        # Создаем связь
        insert_stmt = rooms_facilities.insert().values(room_id=room_id, facility_id=facility_id)
        await self.session.execute(insert_stmt)
        await self.session.flush()  # Убеждаемся, что изменения видны в сессии
        return True

    async def remove_facility(self, room_id: int, facility_id: int) -> bool:
        """
        Удалить удобство из комнаты.

        Args:
            room_id: ID комнаты
            facility_id: ID удобства

        Returns:
            True если связь удалена, False если связи не было

        Raises:
            ValueError: Если комната не найдена
        """
        from src.models.facilities import rooms_facilities

        # Проверяем существование комнаты
        room = await self.get_by_id(room_id)
        if room is None:
            raise ValueError("Комната не найдена")

        # Удаляем связь
        delete_stmt = rooms_facilities.delete().where(
            and_(rooms_facilities.c.room_id == room_id, rooms_facilities.c.facility_id == facility_id)
        )
        result = await self.session.execute(delete_stmt)
        await self.session.flush()  # Убеждаемся, что изменения видны в сессии
        return result.rowcount > 0

    async def get_room_facilities(self, room_id: int) -> list[int]:
        """
        Получить список ID удобств для комнаты.

        Args:
            room_id: ID комнаты

        Returns:
            Список ID удобств

        Raises:
            ValueError: Если комната не найдена
        """
        from src.models.facilities import rooms_facilities

        # Проверяем существование комнаты
        room = await self.get_orm_by_id(room_id)
        if room is None:
            raise ValueError("Комната не найдена")

        # Получаем список ID удобств
        query = select(rooms_facilities.c.facility_id).where(rooms_facilities.c.room_id == room_id)
        result = await self.session.execute(query)
        facility_ids = [row[0] for row in result.fetchall()]
        return facility_ids

    async def update_room_facilities(self, room_id: int, new_facility_ids: list[int]) -> None:
        """
        Эффективно обновить удобства комнаты.

        Удаляет только те удобства, которых нет в новом списке.
        Добавляет только те удобства, которых нет в текущем списке.
        Оставляет нетронутыми те удобства, которые есть в обоих списках.

        Args:
            room_id: ID комнаты
            new_facility_ids: Новый список ID удобств

        Raises:
            ValueError: Если комната не найдена
        """
        from src.models.facilities import rooms_facilities

        # Проверяем существование комнаты
        room = await self.get_orm_by_id(room_id)
        if room is None:
            raise ValueError("Комната не найдена")

        # Получаем текущие связи
        current_facility_ids = await self.get_room_facilities(room_id)
        current_set = set(current_facility_ids)
        new_set = set(new_facility_ids)

        # Находим удобства для удаления (есть в текущих, но нет в новых)
        to_remove = current_set - new_set

        # Находим удобства для добавления (есть в новых, но нет в текущих)
        to_add = new_set - current_set

        # Удаляем только те, что нужно удалить
        if to_remove:
            delete_stmt = rooms_facilities.delete().where(
                and_(rooms_facilities.c.room_id == room_id, rooms_facilities.c.facility_id.in_(to_remove))
            )
            await self.session.execute(delete_stmt)
            await self.session.flush()

        # Добавляем только те, что нужно добавить
        if to_add:
            insert_values = [{"room_id": room_id, "facility_id": facility_id} for facility_id in to_add]
            insert_stmt = rooms_facilities.insert().values(insert_values)
            await self.session.execute(insert_stmt)
            await self.session.flush()
