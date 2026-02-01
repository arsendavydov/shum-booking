from typing import Any

from src.models.rooms import RoomsOrm
from src.repositories.mappers.base import DataMapper
from src.schemas.facilities import SchemaFacility
from src.schemas.rooms import SchemaRoom, SchemaRoomAvailable


def facilities_to_schema(facilities_list) -> list[SchemaFacility]:
    """
    Преобразовать список ORM объектов facilities в список SchemaFacility.

    Использует from_attributes=True для автоматического преобразования.

    Args:
        facilities_list: Список ORM объектов FacilitiesOrm или None

    Returns:
        Список SchemaFacility
    """
    if not facilities_list:
        return []
    return [SchemaFacility.model_validate(f) for f in facilities_list]


class RoomsMapper(DataMapper[RoomsOrm, SchemaRoom]):
    """
    Маппер для преобразования RoomsOrm в SchemaRoom.
    """

    @staticmethod
    def to_schema(orm_obj: RoomsOrm) -> SchemaRoom:
        """
        Преобразовать ORM объект комнаты в Pydantic схему.

        Args:
            orm_obj: ORM объект комнаты

        Returns:
            Pydantic схема SchemaRoom
        """
        facilities = []
        if hasattr(orm_obj, "facilities") and orm_obj.facilities:
            facilities = facilities_to_schema(orm_obj.facilities)

        return SchemaRoom(
            id=orm_obj.id,
            hotel_id=orm_obj.hotel_id,
            title=orm_obj.title,
            description=orm_obj.description,
            price=orm_obj.price,
            quantity=orm_obj.quantity,
            facilities=facilities,
        )

    @staticmethod
    def to_schema_available(orm_obj: RoomsOrm, available_quantity: int) -> SchemaRoomAvailable:
        """
        Преобразовать ORM объект комнаты в Pydantic схему SchemaRoomAvailable.

        Args:
            orm_obj: ORM объект комнаты
            available_quantity: Количество свободных номеров на период

        Returns:
            Pydantic схема SchemaRoomAvailable
        """
        facilities = []
        if hasattr(orm_obj, "facilities") and orm_obj.facilities:
            facilities = facilities_to_schema(orm_obj.facilities)

        return SchemaRoomAvailable(
            id=orm_obj.id,
            hotel_id=orm_obj.hotel_id,
            title=orm_obj.title,
            description=orm_obj.description,
            price=orm_obj.price,
            quantity=available_quantity,
            facilities=facilities,
        )

    @staticmethod
    def from_schema(schema_obj: SchemaRoom, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Преобразовать Pydantic схему комнаты в словарь kwargs для создания ORM объекта.

        Args:
            schema_obj: Pydantic схема SchemaRoom
            exclude: Множество полей, которые нужно исключить из результата

        Returns:
            Словарь kwargs для создания ORM объекта
        """
        exclude = exclude or set()
        exclude.add("id")
        exclude.add("facilities")

        data = schema_obj.model_dump(exclude=exclude)
        return data
