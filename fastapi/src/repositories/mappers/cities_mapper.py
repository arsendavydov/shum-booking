from typing import Any

from src.models.cities import CitiesOrm
from src.repositories.mappers.base import DataMapper
from src.schemas.cities import SchemaCity


class CitiesMapper(DataMapper[CitiesOrm, SchemaCity]):
    """
    Маппер для преобразования CitiesOrm в SchemaCity и обратно.
    """

    @staticmethod
    def to_schema(orm_obj: CitiesOrm) -> SchemaCity:
        """
        Преобразовать ORM объект города в Pydantic схему.

        Args:
            orm_obj: ORM объект города

        Returns:
            Pydantic схема SchemaCity
        """
        from src.schemas.countries import SchemaCountry

        return SchemaCity(
            id=orm_obj.id,
            name=orm_obj.name,
            country=SchemaCountry(id=orm_obj.country.id, name=orm_obj.country.name, iso_code=orm_obj.country.iso_code)
            if orm_obj.country
            else None,
        )

    @staticmethod
    def from_schema(schema_obj: SchemaCity, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Преобразовать Pydantic схему города в словарь kwargs для создания ORM объекта.

        Args:
            schema_obj: Pydantic схема SchemaCity
            exclude: Множество полей, которые нужно исключить из результата

        Returns:
            Словарь kwargs для создания ORM объекта
        """
        exclude = exclude or set()
        exclude.add("id")
        exclude.add("country")

        data = schema_obj.model_dump(exclude=exclude)
        return data
