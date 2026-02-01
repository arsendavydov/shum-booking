from typing import Any

from src.models.hotels import HotelsOrm
from src.repositories.mappers.base import DataMapper
from src.schemas.hotels import SchemaHotel


class HotelsMapper(DataMapper[HotelsOrm, SchemaHotel]):
    """
    Маппер для преобразования HotelsOrm в SchemaHotel и обратно.
    """

    @staticmethod
    def to_schema(orm_obj: HotelsOrm) -> SchemaHotel:
        """
        Преобразовать ORM объект отеля в Pydantic схему.

        Args:
            orm_obj: ORM объект отеля

        Returns:
            Pydantic схема SchemaHotel
        """
        from sqlalchemy import inspect

        city_name = None
        country_name = None

        try:
            insp = inspect(orm_obj)
            if hasattr(insp, "attrs"):
                city_attr = insp.attrs.get("city")
                if city_attr is not None and hasattr(city_attr, "loaded_value"):
                    loaded_val = city_attr.loaded_value
                    if loaded_val is not None:
                        from src.models.cities import CitiesOrm

                        if isinstance(loaded_val, CitiesOrm):
                            city_orm = loaded_val
                            city_name = city_orm.name
                            if city_orm.country:
                                country_name = city_orm.country.name
        except (AttributeError, KeyError, TypeError, ImportError):
            pass

        return SchemaHotel(
            id=orm_obj.id,
            title=orm_obj.title,
            address=orm_obj.address,
            postal_code=orm_obj.postal_code,
            check_in_time=orm_obj.check_in_time,
            check_out_time=orm_obj.check_out_time,
            city=city_name,
            country=country_name,
        )

    @staticmethod
    def from_schema(schema_obj: SchemaHotel, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Преобразовать Pydantic схему отеля в словарь kwargs для создания ORM объекта.

        Args:
            schema_obj: Pydantic схема SchemaHotel
            exclude: Множество полей, которые нужно исключить из результата

        Returns:
            Словарь kwargs для создания ORM объекта
        """
        exclude = exclude or set()
        exclude.add("id")
        exclude.add("city")
        exclude.add("country")

        data = schema_obj.model_dump(exclude=exclude)
        return data
