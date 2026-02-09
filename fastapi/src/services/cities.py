"""
Сервис для работы с городами.

Содержит бизнес-логику создания, обновления и удаления городов.
"""

from src.exceptions.domain import EntityAlreadyExistsError, EntityNotFoundError
from src.schemas.cities import SchemaCity
from src.services.base import BaseService


class CitiesService(BaseService):
    """
    Сервис для работы с городами.

    Инкапсулирует бизнес-логику:
    - Проверка существования страны
    - Проверка уникальности города в стране
    """

    async def create_city(self, name: str, country_id: int) -> SchemaCity:
        """
        Создать город с полной валидацией.

        Args:
            name: Название города
            country_id: ID страны

        Returns:
            Созданный город (Pydantic схема)

        Raises:
            EntityNotFoundError: Если страна не найдена
            EntityAlreadyExistsError: Если город с таким названием в стране уже существует
        """
        # Проверяем существование страны
        country = await self.countries_repo._get_one_by_id_exact(country_id)
        if country is None:
            raise EntityNotFoundError("Страна", entity_id=country_id)

        # Проверяем уникальность города в стране
        existing_city = await self.cities_repo.get_by_name_and_country_id(name, country_id)
        if existing_city is not None:
            raise EntityAlreadyExistsError("Город", "название", name)

        # Создаем город
        return await self.cities_repo.create(name=name, country_id=country_id)

    async def update_city(self, city_id: int, name: str, country_id: int) -> SchemaCity:
        """
        Обновить город с полной валидацией.

        Args:
            city_id: ID города для обновления
            name: Новое название города
            country_id: Новый ID страны

        Returns:
            Обновленный город (Pydantic схема)

        Raises:
            EntityNotFoundError: Если город или страна не найдены
            EntityAlreadyExistsError: Если город с таким названием в стране уже существует
        """
        # Проверяем существование города
        existing_city_orm = await self.cities_repo._get_one_by_id_exact(city_id)
        if existing_city_orm is None:
            raise EntityNotFoundError("Город", entity_id=city_id)

        # Проверяем существование страны
        country = await self.countries_repo._get_one_by_id_exact(country_id)
        if country is None:
            raise EntityNotFoundError("Страна", entity_id=country_id)

        # Проверяем уникальность города в стране, если изменяется name или country_id
        # existing_city_orm - это ORM объект, у него есть country_id
        if name != existing_city_orm.name or country_id != existing_city_orm.country_id:
            existing_city_check = await self.cities_repo.get_by_name_and_country_id(name, country_id)
            if existing_city_check is not None and existing_city_check.id != city_id:
                raise EntityAlreadyExistsError("Город", "название", name)

        # Обновляем город
        updated_city = await self.cities_repo.edit(id=city_id, name=name, country_id=country_id)

        if updated_city is None:
            raise EntityNotFoundError("Город", entity_id=city_id)

        return updated_city

    async def partial_update_city(
        self, city_id: int, name: str | None = None, country_id: int | None = None
    ) -> SchemaCity:
        """
        Частично обновить город с валидацией.

        Args:
            city_id: ID города для обновления
            name: Новое название города (опционально)
            country_id: Новый ID страны (опционально)

        Returns:
            Обновленный город (Pydantic схема)

        Raises:
            EntityNotFoundError: Если город или страна не найдены
            EntityAlreadyExistsError: Если город с таким названием в стране уже существует
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Проверяем существование города с загрузкой связи country
        from src.models.cities import CitiesOrm

        query = select(CitiesOrm).options(selectinload(CitiesOrm.country)).where(CitiesOrm.id == city_id)
        result = await self.session.execute(query)
        existing_city_orm = result.scalar_one_or_none()

        if existing_city_orm is None:
            raise EntityNotFoundError("Город", entity_id=city_id)

        # Получаем существующий город как схему для удобства
        existing_city = self.cities_repo._to_schema(existing_city_orm)

        # Формируем данные для обновления
        from typing import Any

        update_data: dict[str, Any] = {}

        if name is not None:
            update_data["name"] = name
        if country_id is not None:
            update_data["country_id"] = country_id

        if not update_data:
            return existing_city

        # Проверяем и валидируем country_id, если указан
        if "country_id" in update_data:
            country = await self.countries_repo._get_one_by_id_exact(update_data["country_id"])
            if country is None:
                raise EntityNotFoundError("Страна", entity_id=update_data["country_id"])

        # Проверяем уникальность города в стране
        final_name = update_data.get("name", existing_city.name)
        # existing_city - это SchemaCity, у него нет country_id, только country объект
        final_country_id = update_data.get("country_id", existing_city.country.id if existing_city.country else None)

        # Проверяем, изменилось ли что-то, что требует проверки уникальности
        if final_name != existing_city.name or final_country_id != existing_city.country_id:
            existing_city_check = await self.cities_repo.get_by_name_and_country_id(final_name, final_country_id)
            if existing_city_check is not None and existing_city_check.id != city_id:
                raise EntityAlreadyExistsError("Город", "название", final_name)

        # Обновляем город
        updated_city = await self.cities_repo.edit(id=city_id, **update_data)

        if updated_city is None:
            raise EntityNotFoundError("Город", entity_id=city_id)

        return updated_city
