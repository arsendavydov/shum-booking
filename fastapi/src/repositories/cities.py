from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.repositories.base import BaseRepository
from src.repositories.utils import apply_pagination, apply_text_filter
from src.models.cities import CitiesOrm
from src.schemas.cities import SchemaCity
from src.repositories.mappers.cities_mapper import CitiesMapper


class CitiesRepository(BaseRepository[CitiesOrm]):
    """
    Репозиторий для работы с городами.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория городов.
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, CitiesOrm)
    
    def _to_schema(self, orm_obj: CitiesOrm) -> SchemaCity:
        """
        Преобразовать ORM объект города в Pydantic схему.
        
        Args:
            orm_obj: ORM объект города
            
        Returns:
            Pydantic схема SchemaCity
        """
        return CitiesMapper.to_schema(orm_obj)
    
    async def get_paginated(
        self,
        page: int,
        per_page: int,
        name: Optional[str] = None,
        country_id: Optional[int] = None
    ) -> List[SchemaCity]:
        """
        Получить список городов с пагинацией и фильтрацией.
        
        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            name: Опциональный фильтр по названию (частичное совпадение, без учета регистра)
            country_id: Опциональный фильтр по ID страны (точное совпадение)
            
        Returns:
            Список городов (Pydantic схемы)
        """
        from sqlalchemy.orm import selectinload
        
        query = select(self.model).options(
            selectinload(self.model.country)
        )
        
        # Применяем фильтр по name, если указан
        if name is not None:
            query = apply_text_filter(query, self.model.name, name)
        
        # Применяем фильтр по country_id, если указан
        if country_id is not None:
            query = query.where(self.model.country_id == country_id)
        
        # Применяем пагинацию
        query = apply_pagination(query, page, per_page)
        
        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())
        
        return [self._to_schema(obj) for obj in orm_objs]
    
    async def get_by_id(self, id: int) -> Optional[SchemaCity]:
        """
        Получить город по ID с загрузкой связанной страны.
        
        Args:
            id: ID города
            
        Returns:
            Pydantic схема города или None, если не найдено
        """
        from sqlalchemy.orm import selectinload
        
        query = select(self.model).options(
            selectinload(self.model.country)
        ).where(self.model.id == id)
        result = await self.session.execute(query)
        orm_obj = result.scalar_one_or_none()
        
        if orm_obj is None:
            return None
        
        return self._to_schema(orm_obj)
    
    async def get_by_id_orm(self, id: int) -> Optional[CitiesOrm]:
        """
        Получить город по ID как ORM объект (для валидации).
        
        Args:
            id: ID города
            
        Returns:
            ORM объект города или None, если не найдено
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_name_and_country_id(self, name: str, country_id: int) -> Optional[CitiesOrm]:
        """
        Получить город по названию и ID страны.
        
        Args:
            name: Название города
            country_id: ID страны
            
        Returns:
            ORM объект города или None, если не найдено
        """
        from sqlalchemy.orm import selectinload
        
        query = select(self.model).options(
            selectinload(self.model.country)
        ).where(
            self.model.name == name,
            self.model.country_id == country_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_name_case_insensitive(self, name: str) -> Optional[CitiesOrm]:
        """
        Получить город по названию (без учета регистра).
        
        Args:
            name: Название города (может быть в любом регистре)
            
        Returns:
            ORM объект города или None, если не найдено
        """
        from sqlalchemy import func
        
        query = select(self.model).where(
            func.lower(self.model.name) == func.lower(name)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_city_with_validation(
        self,
        name: str,
        country_id: int
    ) -> SchemaCity:
        """
        Создать город с полной валидацией.
        
        Выполняет все проверки и создает город:
        - Проверяет существование страны
        - Проверяет уникальность города в стране
        - Создает город
        
        Args:
            name: Название города
            country_id: ID страны
            
        Returns:
            Созданный город (Pydantic схема)
            
        Raises:
            ValueError: Если страна не найдена или город с таким названием в стране уже существует
        """
        from src.repositories.countries import CountriesRepository
        
        # Проверяем существование страны
        countries_repo = CountriesRepository(self.session)
        country = await countries_repo._get_one_by_id_exact(country_id)
        if country is None:
            raise ValueError(f"Страна с ID {country_id} не найдена")
        
        # Проверяем уникальность города в стране
        existing_city = await self.get_by_name_and_country_id(name, country_id)
        if existing_city is not None:
            raise ValueError(f"Город '{name}' в стране с ID {country_id} уже существует")
        
        # Создаем город
        return await self.create(name=name, country_id=country_id)
    
    async def update_city_with_validation(
        self,
        city_id: int,
        name: str,
        country_id: int
    ) -> SchemaCity:
        """
        Обновить город с полной валидацией.
        
        Выполняет все проверки и обновляет город:
        - Проверяет существование города
        - Проверяет существование страны
        - Проверяет уникальность города в стране (если изменяется name или country_id)
        - Обновляет город
        
        Args:
            city_id: ID города для обновления
            name: Новое название города
            country_id: Новый ID страны
            
        Returns:
            Обновленный город (Pydantic схема)
            
        Raises:
            ValueError: Если город или страна не найдены, или город с таким названием в стране уже существует
        """
        # Проверяем существование города
        existing_city_orm = await self._get_one_by_id_exact(city_id)
        if existing_city_orm is None:
            raise ValueError("Город не найден")
        
        from src.repositories.countries import CountriesRepository
        
        # Проверяем существование страны
        countries_repo = CountriesRepository(self.session)
        country = await countries_repo._get_one_by_id_exact(country_id)
        if country is None:
            raise ValueError(f"Страна с ID {country_id} не найдена")
        
        # Проверяем уникальность города в стране, если изменяется name или country_id
        if name != existing_city_orm.name or country_id != existing_city_orm.country_id:
            existing_city_check = await self.get_by_name_and_country_id(name, country_id)
            if existing_city_check is not None and existing_city_check.id != city_id:
                raise ValueError(f"Город '{name}' в стране с ID {country_id} уже существует")
        
        # Обновляем город
        updated_city = await self.edit(
            id=city_id,
            name=name,
            country_id=country_id
        )
        
        if updated_city is None:
            raise ValueError("Город не найден")
        
        return updated_city
    
    async def partial_update_city_with_validation(
        self,
        city_id: int,
        name: Optional[str] = None,
        country_id: Optional[int] = None
    ) -> SchemaCity:
        """
        Частично обновить город с полной валидацией.
        
        Выполняет все проверки и частично обновляет город:
        - Проверяет существование города
        - Проверяет существование страны (если передан country_id)
        - Проверяет уникальность города в стране (если изменяется name или country_id)
        - Обновляет только переданные поля
        
        Args:
            city_id: ID города для обновления
            name: Новое название города (опционально)
            country_id: Новый ID страны (опционально)
            
        Returns:
            Обновленный город (Pydantic схема)
            
        Raises:
            ValueError: Если город или страна не найдены, или город с таким названием в стране уже существует
        """
        from sqlalchemy.orm import selectinload
        
        # Проверяем существование города с загрузкой связи country
        query = select(self.model).options(
            selectinload(self.model.country)
        ).where(self.model.id == city_id)
        result = await self.session.execute(query)
        existing_city_orm = result.scalar_one_or_none()
        
        if existing_city_orm is None:
            raise ValueError("Город не найден")
        
        # Получаем существующий город как схему для удобства
        existing_city = self._to_schema(existing_city_orm)
        
        # Формируем данные для обновления
        update_data: Dict[str, Any] = {}
        
        if name is not None:
            update_data["name"] = name
        if country_id is not None:
            update_data["country_id"] = country_id
        
        if not update_data:
            return existing_city
        
        # Проверяем и валидируем country_id, если указан
        if "country_id" in update_data:
            from src.repositories.countries import CountriesRepository
            countries_repo = CountriesRepository(self.session)
            country = await countries_repo._get_one_by_id_exact(update_data["country_id"])
            if country is None:
                raise ValueError(f"Страна с ID {update_data['country_id']} не найдена")
        
        # Проверяем уникальность города в стране
        final_name = update_data.get("name", existing_city.name)
        final_country_id = update_data.get("country_id", existing_city.country_id)
        
        # Проверяем, изменилось ли что-то, что требует проверки уникальности
        if final_name != existing_city.name or final_country_id != existing_city.country_id:
            existing_city_check = await self.get_by_name_and_country_id(final_name, final_country_id)
            if existing_city_check is not None and existing_city_check.id != city_id:
                raise ValueError(f"Город '{final_name}' в стране с ID {final_country_id} уже существует")
        
        # Обновляем город
        updated_city = await self.edit(id=city_id, **update_data)
        
        if updated_city is None:
            raise ValueError("Город не найден")
        
        return updated_city

