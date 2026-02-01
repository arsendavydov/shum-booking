from typing import Any

from src.models.facilities import FacilitiesOrm
from src.repositories.mappers.base import DataMapper
from src.schemas.facilities import SchemaFacility


class FacilitiesMapper(DataMapper[FacilitiesOrm, SchemaFacility]):
    """
    Маппер для преобразования FacilitiesOrm в SchemaFacility и обратно.
    """

    @staticmethod
    def to_schema(orm_obj: FacilitiesOrm) -> SchemaFacility:
        """
        Преобразовать ORM объект удобства в Pydantic схему.

        Использует from_attributes=True для автоматического преобразования.

        Args:
            orm_obj: ORM объект удобства

        Returns:
            Pydantic схема SchemaFacility
        """
        return SchemaFacility.model_validate(orm_obj)

    @staticmethod
    def from_schema(schema_obj: SchemaFacility, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Преобразовать Pydantic схему удобства в словарь kwargs для создания ORM объекта.

        Args:
            schema_obj: Pydantic схема SchemaFacility
            exclude: Множество полей, которые нужно исключить из результата

        Returns:
            Словарь kwargs для создания ORM объекта
        """
        exclude = exclude or set()
        exclude.add("id")

        data = schema_obj.model_dump(exclude=exclude)
        return data
