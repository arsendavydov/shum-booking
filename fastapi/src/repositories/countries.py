from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.countries import CountriesOrm
from src.repositories.base import BaseRepository
from src.repositories.mappers.countries_mapper import CountriesMapper
from src.repositories.utils import apply_pagination, apply_text_filter
from src.schemas.countries import SchemaCountry


class CountriesRepository(BaseRepository[CountriesOrm]):
    """
    Репозиторий для работы со странами.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория стран.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, CountriesOrm)

    def _to_schema(self, orm_obj: CountriesOrm) -> SchemaCountry:
        """
        Преобразовать ORM объект страны в Pydantic схему.

        Args:
            orm_obj: ORM объект страны

        Returns:
            Pydantic схема SchemaCountry
        """
        return CountriesMapper.to_schema(orm_obj)

    async def get_paginated(self, page: int, per_page: int, name: str | None = None) -> list[SchemaCountry]:
        """
        Получить список стран с пагинацией и фильтрацией.

        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            name: Опциональный фильтр по названию (частичное совпадение, без учета регистра)

        Returns:
            Список стран (Pydantic схемы)
        """
        query = select(self.model)

        # Применяем фильтр по name, если указан
        if name is not None:
            query = apply_text_filter(query, self.model.name, name)

        # Применяем пагинацию
        query = apply_pagination(query, page, per_page)

        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())

        return [self._to_schema(obj) for obj in orm_objs]

    async def get_by_iso_code(self, iso_code: str) -> CountriesOrm | None:
        """
        Получить страну по ISO коду.

        Args:
            iso_code: ISO 3166-1 alpha-2 код страны (2 буквы)

        Returns:
            ORM объект страны или None, если не найдено
        """
        query = select(self.model).where(self.model.iso_code == iso_code.upper())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name_case_insensitive(self, name: str) -> CountriesOrm | None:
        """
        Получить страну по названию (без учета регистра).

        Args:
            name: Название страны (может быть в любом регистре)

        Returns:
            ORM объект страны или None, если не найдено
        """
        from sqlalchemy import func

        query = select(self.model).where(func.lower(self.model.name) == func.lower(name))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_country_with_validation(self, name: str, iso_code: str) -> SchemaCountry:
        """
        Создать страну с полной валидацией.

        Выполняет все проверки и создает страну:
        - Проверяет уникальность name
        - Проверяет уникальность iso_code
        - Создает страну

        Args:
            name: Название страны
            iso_code: ISO код страны (2 буквы)

        Returns:
            Созданная страна (Pydantic схема)

        Raises:
            ValueError: Если страна с таким названием или ISO кодом уже существует
        """
        # Проверяем уникальность name
        existing_by_name = await self.get_by_name_case_insensitive(name)
        if existing_by_name is not None:
            raise ValueError(f"Страна с названием '{name}' уже существует")

        # Проверяем уникальность iso_code
        existing_by_iso = await self.get_by_iso_code(iso_code)
        if existing_by_iso is not None:
            raise ValueError(f"Страна с ISO кодом '{iso_code.upper()}' уже существует")

        # Создаем страну
        return await self.create(name=name, iso_code=iso_code.upper())

    async def update_country_with_validation(self, country_id: int, name: str, iso_code: str) -> SchemaCountry:
        """
        Обновить страну с полной валидацией.

        Выполняет все проверки и обновляет страну:
        - Проверяет существование страны
        - Проверяет уникальность name (если изменяется)
        - Проверяет уникальность iso_code (если изменяется)
        - Обновляет страну

        Args:
            country_id: ID страны для обновления
            name: Новое название страны
            iso_code: Новый ISO код страны (2 буквы)

        Returns:
            Обновленная страна (Pydantic схема)

        Raises:
            ValueError: Если страна не найдена или страна с таким названием/ISO кодом уже существует
        """
        # Проверяем существование страны
        existing_country = await self._get_one_by_id_exact(country_id)
        if existing_country is None:
            raise ValueError("Страна не найдена")

        # Проверяем уникальность name, если он изменяется
        if name != existing_country.name:
            existing_by_name = await self.get_by_name_case_insensitive(name)
            if existing_by_name is not None:
                raise ValueError(f"Страна с названием '{name}' уже существует")

        # Проверяем уникальность iso_code, если он изменяется
        iso_code_upper = iso_code.upper()
        if iso_code_upper != existing_country.iso_code:
            existing_by_iso = await self.get_by_iso_code(iso_code)
            if existing_by_iso is not None:
                raise ValueError(f"Страна с ISO кодом '{iso_code_upper}' уже существует")

        # Обновляем страну
        updated_country = await self.edit(id=country_id, name=name, iso_code=iso_code_upper)

        if updated_country is None:
            raise ValueError("Страна не найдена")

        return updated_country

    async def partial_update_country_with_validation(
        self, country_id: int, name: str | None = None, iso_code: str | None = None
    ) -> SchemaCountry:
        """
        Частично обновить страну с полной валидацией.

        Выполняет все проверки и частично обновляет страну:
        - Проверяет существование страны
        - Проверяет уникальность name (если изменяется)
        - Проверяет уникальность iso_code (если изменяется)
        - Обновляет только переданные поля

        Args:
            country_id: ID страны для обновления
            name: Новое название страны (опционально)
            iso_code: Новый ISO код страны (опционально, 2 буквы)

        Returns:
            Обновленная страна (Pydantic схема)

        Raises:
            ValueError: Если страна не найдена или страна с таким названием/ISO кодом уже существует
        """
        # Проверяем существование страны
        existing_country = await self._get_one_by_id_exact(country_id)
        if existing_country is None:
            raise ValueError("Страна не найдена")

        update_data: dict[str, Any] = {}

        # Проверяем и добавляем name, если указан
        if name is not None:
            if name != existing_country.name:
                existing_by_name = await self.get_by_name_case_insensitive(name)
                if existing_by_name is not None:
                    raise ValueError(f"Страна с названием '{name}' уже существует")
            update_data["name"] = name

        # Проверяем и добавляем iso_code, если указан
        if iso_code is not None:
            iso_code_upper = iso_code.upper()
            if iso_code_upper != existing_country.iso_code:
                existing_by_iso = await self.get_by_iso_code(iso_code)
                if existing_by_iso is not None:
                    raise ValueError(f"Страна с ISO кодом '{iso_code_upper}' уже существует")
            update_data["iso_code"] = iso_code_upper

        if not update_data:
            return self._to_schema(existing_country)

        # Обновляем страну
        updated_country = await self.edit(id=country_id, **update_data)

        if updated_country is None:
            raise ValueError("Страна не найдена")

        return updated_country
