from typing import Any

from src.models.countries import CountriesOrm
from src.repositories.mappers.base import DataMapper
from src.schemas.countries import SchemaCountry


class CountriesMapper(DataMapper[CountriesOrm, SchemaCountry]):
    """
    Маппер для преобразования CountriesOrm в SchemaCountry и обратно.
    """

    @staticmethod
    def to_schema(orm_obj: CountriesOrm) -> SchemaCountry:
        """
        Преобразовать ORM объект страны в Pydantic схему.

        Args:
            orm_obj: ORM объект страны

        Returns:
            Pydantic схема SchemaCountry
        """
        return SchemaCountry(id=orm_obj.id, name=orm_obj.name, iso_code=orm_obj.iso_code)

    @staticmethod
    def from_schema(schema_obj: SchemaCountry, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Преобразовать Pydantic схему страны в словарь kwargs для создания ORM объекта.

        Args:
            schema_obj: Pydantic схема SchemaCountry
            exclude: Множество полей, которые нужно исключить из результата

        Returns:
            Словарь kwargs для создания ORM объекта
        """
        exclude = exclude or set()
        exclude.add("id")

        data = schema_obj.model_dump(exclude=exclude)
        return data
