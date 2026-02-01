from typing import Any, Generic, TypeVar

from sqlalchemy.orm import DeclarativeBase

# Generic типы для ORM модели и Pydantic схемы
OrmType = TypeVar("OrmType", bound=DeclarativeBase)
SchemaType = TypeVar("SchemaType")


class DataMapper(Generic[OrmType, SchemaType]):
    """
    Базовый класс для преобразования ORM объектов в Pydantic схемы и обратно (Data Mapper паттерн).

    Каждый маппер должен переопределить методы to_schema и from_schema для конкретной пары ORM-Schema.
    """

    @staticmethod
    def to_schema(orm_obj: OrmType) -> SchemaType:
        """
        Преобразовать ORM объект в Pydantic схему.

        Должен быть переопределен в дочерних классах.

        Args:
            orm_obj: ORM объект для преобразования

        Returns:
            Pydantic схема

        Raises:
            NotImplementedError: Если метод не переопределен
        """
        raise NotImplementedError("Метод to_schema должен быть переопределен в дочернем классе")

    @staticmethod
    def from_schema(schema_obj: SchemaType, exclude: set[str] | None = None) -> dict[str, Any]:
        """
        Преобразовать Pydantic схему в словарь kwargs для создания ORM объекта.

        Должен быть переопределен в дочерних классах.

        Args:
            schema_obj: Pydantic схема для преобразования
            exclude: Множество полей, которые нужно исключить из результата

        Returns:
            Словарь kwargs для создания ORM объекта

        Raises:
            NotImplementedError: Если метод не переопределен
        """
        raise NotImplementedError("Метод from_schema должен быть переопределен в дочернем классе")

    @staticmethod
    def to_schema_list(orm_objs: list[OrmType]) -> list[SchemaType]:
        """
        Преобразовать список ORM объектов в список Pydantic схем.

        Args:
            orm_objs: Список ORM объектов

        Returns:
            Список Pydantic схем
        """
        return [DataMapper.to_schema(obj) for obj in orm_objs]
