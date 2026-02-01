from typing import Optional, List, Dict, Any
from datetime import date, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.repositories.base import BaseRepository
from src.repositories.utils import apply_pagination, apply_text_filter
from src.models.hotels import HotelsOrm
from src.schemas.hotels import SchemaHotel, SchemaHotelWithRooms
from src.repositories.mappers.hotels_mapper import HotelsMapper


class HotelsRepository(BaseRepository[HotelsOrm]):
    """
    Репозиторий для работы с отелями.
    
    Наследует базовые CRUD методы и добавляет специфичные методы
    для работы с отелями (фильтрация, пагинация).
    """
    
    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория отелей.
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, HotelsOrm)
    
    def _to_schema(self, orm_obj: HotelsOrm) -> SchemaHotel:
        """
        Преобразовать ORM объект отеля в Pydantic схему.
        
        Args:
            orm_obj: ORM объект отеля
            
        Returns:
            Pydantic схема SchemaHotel
        """
        return HotelsMapper.to_schema(orm_obj)
    
    async def get_by_title(self, title: str) -> List[SchemaHotel]:
        """
        Получить отели по названию (точное совпадение).
        
        Args:
            title: Название отеля
            
        Returns:
            Список отелей (Pydantic схемы)
        """
        from sqlalchemy.orm import selectinload
        from src.models.cities import CitiesOrm
        
        query = select(self.model).options(
            selectinload(self.model.city).selectinload(CitiesOrm.country)
        ).where(self.model.title == title)
        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())
        return [self._to_schema(obj) for obj in orm_objs]
    
    async def get_by_city_id(self, city_id: int) -> List[SchemaHotel]:
        """
        Получить отели по ID города.
        
        Args:
            city_id: ID города
            
        Returns:
            Список отелей (Pydantic схемы)
        """
        from sqlalchemy.orm import selectinload
        from src.models.cities import CitiesOrm
        
        query = select(self.model).options(
            selectinload(self.model.city).selectinload(CitiesOrm.country)
        ).where(self.model.city_id == city_id)
        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())
        return [self._to_schema(obj) for obj in orm_objs]
    
    async def get_paginated(
        self,
        page: int,
        per_page: int,
        title: Optional[str] = None,
        city: Optional[str] = None,
        city_id: Optional[int] = None,
        sort_by: str = "id",
        order: str = "asc"
    ) -> List[SchemaHotel]:
        """
        Получить список отелей с пагинацией, фильтрацией и сортировкой.
        
        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            title: Опциональный фильтр по названию (частичное совпадение, без учета регистра)
            city: Опциональный фильтр по названию города (частичное совпадение, без учета регистра)
            city_id: Опциональный фильтр по ID города
            sort_by: Поле для сортировки ("id", "title", "city") - по умолчанию "id"
            order: Направление сортировки ("asc" или "desc") - по умолчанию "asc"
            
        Returns:
            Список отелей (Pydantic схемы)
        """
        from sqlalchemy.orm import selectinload
        from src.models.cities import CitiesOrm
        
        query = select(self.model).options(
            selectinload(self.model.city).selectinload(CitiesOrm.country)
        )
        
        # Применяем фильтры
        if title is not None:
            query = apply_text_filter(query, self.model.title, title)
        if city is not None:
            query = query.join(CitiesOrm, self.model.city_id == CitiesOrm.id)
            query = apply_text_filter(query, CitiesOrm.name, city)
        if city_id is not None:
            query = query.where(self.model.city_id == city_id)
        
        # Применяем сортировку
        sort_field = None
        if sort_by == "title":
            sort_field = self.model.title
        elif sort_by == "city":
            if city is None and city_id is None:
                query = query.join(CitiesOrm, self.model.city_id == CitiesOrm.id)
            sort_field = CitiesOrm.name
        else:  # по умолчанию "id"
            sort_field = self.model.id
        
        if order.lower() == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())
        
        # Применяем пагинацию
        query = apply_pagination(query, page, per_page)
        
        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())
        
        return [self._to_schema(obj) for obj in orm_objs]
    
    async def count(
        self,
        title: Optional[str] = None,
        city: Optional[str] = None
    ) -> int:
        """
        Подсчитать количество отелей с учетом фильтров.
        
        Args:
            title: Опциональный фильтр по названию
            city: Опциональный фильтр по названию города (частичное совпадение, без учета регистра)
            
        Returns:
            Количество отелей
        """
        from src.models.cities import CitiesOrm
        
        query = select(func.count(self.model.id))
        
        if title is not None:
            query = apply_text_filter(query, self.model.title, title)
        if city is not None:
            # Фильтрация по названию города с частичным совпадением без учета регистра
            query = query.join(CitiesOrm, self.model.city_id == CitiesOrm.id)
            query = apply_text_filter(query, CitiesOrm.name, city)
        
        result = await self.session.execute(query)
        return result.scalar_one() or 0
    
    async def get_by_id(self, id: int) -> Optional[SchemaHotel]:
        """
        Получить отель по ID с загрузкой связанного города.
        
        Args:
            id: ID отеля
            
        Returns:
            Pydantic схема отеля или None, если не найдено
        """
        from sqlalchemy.orm import selectinload
        from src.models.cities import CitiesOrm
        
        query = select(self.model).options(
            selectinload(self.model.city).selectinload(CitiesOrm.country)
        ).where(self.model.id == id)
        result = await self.session.execute(query)
        orm_obj = result.scalar_one_or_none()
        
        if orm_obj is None:
            return None
        
        return self._to_schema(orm_obj)
    
    async def exists_by_title(self, title: str, exclude_hotel_id: Optional[int] = None) -> bool:
        """
        Проверить существование отеля с указанным названием.
        
        Args:
            title: Название отеля
            exclude_hotel_id: ID отеля, который нужно исключить из проверки (для обновления)
            
        Returns:
            True если отель с таким названием существует, False иначе
        """
        query = select(self.model).where(self.model.title == title)
        if exclude_hotel_id is not None:
            query = query.where(self.model.id != exclude_hotel_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_hotels_with_available_rooms(
        self,
        date_from: date,
        date_to: date,
        page: int,
        per_page: int,
        hotel_id: Optional[int] = None,
        title: Optional[str] = None,
        city: Optional[str] = None
    ) -> List[SchemaHotelWithRooms]:
        """
        Получить отели с доступными комнатами на указанный период с поддержкой пагинации и фильтрации.
        
        Для каждого отеля возвращается список комнат с актуальным количеством
        свободных номеров на указанный период. Комнаты с quantity=0 не возвращаются.
        
        Args:
            date_from: Дата начала периода
            date_to: Дата окончания периода
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            hotel_id: Опциональный ID отеля. Если указан, возвращается только этот отель.
            title: Опциональный фильтр по названию отеля (частичное совпадение, без учета регистра)
            city: Опциональный фильтр по названию города (частичное совпадение, без учета регистра)
            
        Returns:
            Список отелей с комнатами и актуальным количеством свободных номеров
        """
        from sqlalchemy.orm import selectinload
        from src.models.cities import CitiesOrm
        
        # Формируем запрос для получения отелей
        query = select(self.model).options(
            selectinload(self.model.city).selectinload(CitiesOrm.country)
        )
        
        # Применяем фильтры
        if hotel_id is not None:
            query = query.where(self.model.id == hotel_id)
        if title is not None:
            query = apply_text_filter(query, self.model.title, title)
        if city is not None:
            # Фильтрация по названию города с частичным совпадением без учета регистра
            query = query.join(CitiesOrm, self.model.city_id == CitiesOrm.id)
            query = apply_text_filter(query, CitiesOrm.name, city)
        
        # Применяем пагинацию
        query = apply_pagination(query, page, per_page)
        
        result = await self.session.execute(query)
        hotels_orm = list(result.scalars().all())
        
        if not hotels_orm:
            return []
        
        # Создаем репозиторий комнат для расчета доступности (импортируем локально, чтобы избежать циклических импортов)
        from src.repositories.rooms import RoomsRepository
        rooms_repo = RoomsRepository(self.session)
        
        # Для каждого отеля получаем комнаты с актуальным количеством
        hotels_with_rooms = []
        for hotel_orm in hotels_orm:
            # Получаем все комнаты отеля с актуальным количеством
            rooms = await rooms_repo.get_rooms_with_availability(
                hotel_id=hotel_orm.id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Преобразуем отель в схему
            hotel_schema = self._to_schema(hotel_orm)
            
            # Создаем схему отеля с комнатами
            hotel_with_rooms = SchemaHotelWithRooms(
                id=hotel_schema.id,
                title=hotel_schema.title,
                address=hotel_schema.address,
                postal_code=hotel_schema.postal_code,
                check_in_time=hotel_schema.check_in_time,
                check_out_time=hotel_schema.check_out_time,
                city=hotel_schema.city,
                country=hotel_schema.country,
                rooms=rooms
            )
            hotels_with_rooms.append(hotel_with_rooms)
        
        return hotels_with_rooms
    
    async def create_hotel_with_validation(
        self,
        title: str,
        city_name: str,
        address: str,
        postal_code: Optional[str] = None,
        check_in_time: Optional[time] = None,
        check_out_time: Optional[time] = None
    ) -> SchemaHotel:
        """
        Создать отель с полной валидацией.
        
        Выполняет все проверки и создает отель:
        - Валидирует существование города по названию (без учета регистра)
        - Проверяет уникальность title
        - Устанавливает дефолтные значения для check_in_time и check_out_time
        - Создает отель
        
        Args:
            title: Название отеля
            city_name: Название города (без учета регистра)
            address: Адрес отеля
            postal_code: Почтовый индекс (опционально)
            check_in_time: Время заезда (опционально, по умолчанию 14:00)
            check_out_time: Время выезда (опционально, по умолчанию 12:00)
            
        Returns:
            Созданный отель (Pydantic схема)
            
        Raises:
            ValueError: Если город не найден или отель с таким title уже существует
        """
        from src.repositories.cities import CitiesRepository
        
        # Валидируем существование города
        cities_repo = CitiesRepository(self.session)
        city_orm = await cities_repo.get_by_name_case_insensitive(city_name)
        if city_orm is None:
            raise ValueError(f"Город '{city_name}' не найден")
        
        # Проверяем уникальность title
        if await self.exists_by_title(title):
            raise ValueError(f"Отель с названием '{title}' уже существует")
        
        # Устанавливаем дефолтные значения
        if check_in_time is None:
            check_in_time = time(14, 0)
        if check_out_time is None:
            check_out_time = time(12, 0)
        
        # Создаем отель
        hotel_data = {
            "title": title,
            "city_id": city_orm.id,
            "address": address,
            "postal_code": postal_code,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time
        }
        
        return await self.create(**hotel_data)
    
    async def update_hotel_with_validation(
        self,
        hotel_id: int,
        title: str,
        city_name: str,
        address: str,
        postal_code: Optional[str] = None,
        check_in_time: Optional[time] = None,
        check_out_time: Optional[time] = None
    ) -> SchemaHotel:
        """
        Обновить отель с полной валидацией.
        
        Выполняет все проверки и обновляет отель:
        - Проверяет существование отеля
        - Валидирует существование города по названию (без учета регистра)
        - Проверяет уникальность title (если изменяется)
        - Обновляет отель
        
        Args:
            hotel_id: ID отеля для обновления
            title: Новое название отеля
            city_name: Название города (без учета регистра)
            address: Новый адрес отеля
            postal_code: Почтовый индекс (опционально)
            check_in_time: Время заезда (опционально)
            check_out_time: Время выезда (опционально)
            
        Returns:
            Обновленный отель (Pydantic схема)
            
        Raises:
            ValueError: Если отель не найден, город не найден или отель с таким title уже существует
        """
        # Проверяем существование отеля
        existing_hotel = await self.get_by_id(hotel_id)
        if existing_hotel is None:
            raise ValueError("Отель не найден")
        
        from src.repositories.cities import CitiesRepository
        
        # Валидируем существование города
        cities_repo = CitiesRepository(self.session)
        city_orm = await cities_repo.get_by_name_case_insensitive(city_name)
        if city_orm is None:
            raise ValueError(f"Город '{city_name}' не найден")
        
        # Проверяем уникальность title, если он изменяется
        if title != existing_hotel.title:
            if await self.exists_by_title(title, exclude_hotel_id=hotel_id):
                raise ValueError(f"Отель с названием '{title}' уже существует")
        
        # Обновляем отель
        try:
            updated_hotel = await self.edit(
                id=hotel_id,
                title=title,
                city_id=city_orm.id,
                address=address,
                postal_code=postal_code,
                check_in_time=check_in_time,
                check_out_time=check_out_time
            )
        except ValueError as e:
            raise ValueError(str(e))
        
        if updated_hotel is None:
            raise ValueError("Отель не найден")
        
        return updated_hotel
    
    async def partial_update_hotel_with_validation(
        self,
        hotel_id: int,
        title: Optional[str] = None,
        city_name: Optional[str] = None,
        address: Optional[str] = None,
        postal_code: Optional[str] = None,
        check_in_time: Optional[time] = None,
        check_out_time: Optional[time] = None
    ) -> SchemaHotel:
        """
        Частично обновить отель с полной валидацией.
        
        Выполняет все проверки и частично обновляет отель:
        - Проверяет существование отеля
        - Валидирует существование города (если передан city_name)
        - Проверяет уникальность title (если изменяется)
        - Обновляет только переданные поля
        
        Args:
            hotel_id: ID отеля для обновления
            title: Новое название отеля (опционально)
            city_name: Название города (опционально, без учета регистра)
            address: Новый адрес отеля (опционально)
            postal_code: Почтовый индекс (опционально)
            check_in_time: Время заезда (опционально)
            check_out_time: Время выезда (опционально)
            
        Returns:
            Обновленный отель (Pydantic схема)
            
        Raises:
            ValueError: Если отель не найден, город не найден или отель с таким title уже существует
        """
        # Проверяем существование отеля
        existing_hotel = await self.get_by_id(hotel_id)
        if existing_hotel is None:
            raise ValueError("Отель не найден")
        
        # Формируем данные для обновления
        update_data: Dict[str, Any] = {}
        
        if title is not None:
            update_data["title"] = title
        if address is not None:
            update_data["address"] = address
        if postal_code is not None:
            update_data["postal_code"] = postal_code
        if check_in_time is not None:
            update_data["check_in_time"] = check_in_time
        if check_out_time is not None:
            update_data["check_out_time"] = check_out_time
        
        # Валидируем город, если передан
        if city_name is not None:
            from src.repositories.cities import CitiesRepository
            cities_repo = CitiesRepository(self.session)
            city_orm = await cities_repo.get_by_name_case_insensitive(city_name)
            if city_orm is None:
                raise ValueError(f"Город '{city_name}' не найден")
            update_data["city_id"] = city_orm.id
        
        # Проверяем уникальность title, если он изменяется
        if "title" in update_data and update_data["title"] != existing_hotel.title:
            if await self.exists_by_title(update_data["title"], exclude_hotel_id=hotel_id):
                raise ValueError(f"Отель с названием '{update_data['title']}' уже существует")
        
        # Обновляем отель, если есть что обновлять
        if update_data:
            await self.update(id=hotel_id, **update_data)
        
        # Возвращаем обновленный отель
        updated_hotel = await self.get_by_id(hotel_id)
        if updated_hotel is None:
            raise ValueError("Отель не найден")
        
        return updated_hotel

