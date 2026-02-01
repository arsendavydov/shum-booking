from typing import Any

from src.models.bookings import BookingsOrm
from src.repositories.mappers.base import DataMapper
from src.schemas.bookings import SchemaBooking


class BookingsMapper(DataMapper[BookingsOrm, SchemaBooking]):
    """
    Маппер для преобразования BookingsOrm в SchemaBooking и обратно.
    """

    @staticmethod
    def to_schema(orm_obj: BookingsOrm) -> SchemaBooking:
        """
        Преобразовать ORM объект бронирования в Pydantic схему.

        Args:
            orm_obj: ORM объект бронирования

        Returns:
            Pydantic схема SchemaBooking
        """
        return SchemaBooking(
            id=orm_obj.id,
            room_id=orm_obj.room_id,
            user_id=orm_obj.user_id,
            date_from=orm_obj.date_from,
            date_to=orm_obj.date_to,
            price=orm_obj.price,
            created_at=orm_obj.created_at,
        )

    @staticmethod
    def from_schema(schema_obj: SchemaBooking, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Преобразовать Pydantic схему бронирования в словарь kwargs для создания ORM объекта.

        Args:
            schema_obj: Pydantic схема SchemaBooking
            exclude: Множество полей, которые нужно исключить из результата

        Returns:
            Словарь kwargs для создания ORM объекта
        """
        exclude = exclude or set()
        exclude.add("id")
        exclude.add("created_at")

        data = schema_obj.model_dump(exclude=exclude)
        return data
