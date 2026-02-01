from typing import Any

from src.models.users import UsersOrm
from src.repositories.mappers.base import DataMapper
from src.schemas.users import SchemaUser, UserRegister


class UsersMapper(DataMapper[UsersOrm, SchemaUser]):
    """
    Маппер для преобразования UsersOrm в SchemaUser и обратно.
    """

    @staticmethod
    def to_schema(orm_obj: UsersOrm) -> SchemaUser:
        """
        Преобразовать ORM объект пользователя в Pydantic схему.

        Args:
            orm_obj: ORM объект пользователя

        Returns:
            Pydantic схема SchemaUser (без пароля)
        """
        return SchemaUser(
            id=orm_obj.id,
            email=orm_obj.email,
            first_name=orm_obj.first_name,
            last_name=orm_obj.last_name,
            telegram_id=orm_obj.telegram_id,
            pachca_id=orm_obj.pachca_id,
        )

    @staticmethod
    def from_schema(schema_obj: UserRegister, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Преобразовать Pydantic схему пользователя в словарь kwargs для создания ORM объекта.

        Args:
            schema_obj: Pydantic схема UserRegister
            exclude: Множество полей, которые нужно исключить из результата

        Returns:
            Словарь kwargs для создания ORM объекта
        """
        exclude = exclude or set()
        exclude.add("id")

        data = schema_obj.model_dump(exclude=exclude)
        return data
