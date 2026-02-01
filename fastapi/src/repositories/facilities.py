from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.facilities import FacilitiesOrm
from src.repositories.base import BaseRepository
from src.repositories.mappers.facilities_mapper import FacilitiesMapper
from src.repositories.utils import apply_pagination, apply_text_filter
from src.schemas.facilities import SchemaFacility


class FacilitiesRepository(BaseRepository[FacilitiesOrm]):
    """
    Репозиторий для работы с удобствами (facilities).

    Наследует базовые CRUD методы и добавляет специфичные методы
    для работы с удобствами.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория удобств.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, FacilitiesOrm)

    def _to_schema(self, orm_obj: FacilitiesOrm) -> SchemaFacility:
        """
        Преобразовать ORM объект удобства в Pydantic схему.

        Args:
            orm_obj: ORM объект удобства

        Returns:
            Pydantic схема SchemaFacility
        """
        return FacilitiesMapper.to_schema(orm_obj)

    async def get_paginated(self, page: int, per_page: int, title: str | None = None) -> list[SchemaFacility]:
        """
        Получить список удобств с пагинацией и фильтрацией.

        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            title: Опциональный фильтр по названию (частичное совпадение, без учета регистра)

        Returns:
            Список удобств (Pydantic схемы)
        """
        query = select(self.model)

        # Применяем фильтр по title, если указан
        if title is not None:
            query = apply_text_filter(query, self.model.title, title)

        # Применяем пагинацию
        query = apply_pagination(query, page, per_page)

        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())

        return [self._to_schema(obj) for obj in orm_objs]
