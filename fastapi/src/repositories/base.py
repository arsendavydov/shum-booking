from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Generic тип для ORM модели
ModelType = TypeVar("ModelType", bound=DeclarativeBase)
# Generic тип для Pydantic схемы
SchemaType = TypeVar("SchemaType")


class BaseRepository(Generic[ModelType]):
    """
    Базовый репозиторий для работы с базой данных.

    Предоставляет общие методы CRUD операций для всех моделей.
    """

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        """
        Инициализация репозитория.

        Args:
            session: Асинхронная сессия SQLAlchemy
            model: Класс ORM модели
        """
        self.session = session
        self.model = model

    def _to_schema(self, orm_obj: ModelType) -> Any:
        """
        Преобразовать ORM объект в Pydantic схему.

        Должен быть переопределен в дочерних классах для конкретной схемы.

        Args:
            orm_obj: ORM объект для преобразования

        Returns:
            Pydantic схема

        Raises:
            NotImplementedError: Если метод не переопределен
        """
        raise NotImplementedError("Метод _to_schema должен быть переопределен в дочернем классе")

    async def create(self, **kwargs: Any) -> Any:
        """
        Создать новую запись.

        Возвращает Pydantic схему через Data Mapper паттерн.
        Метод _to_schema должен быть переопределен в дочернем классе.

        Args:
            **kwargs: Поля для создания записи

        Returns:
            Созданная Pydantic схема

        Raises:
            NotImplementedError: Если метод _to_schema не переопределен
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)

        return self._to_schema(instance)

    async def _get_one_by_id_exact(self, id: int) -> ModelType | None:
        """
        Получить ровно один объект по ID с проверкой.

        Args:
            id: ID записи

        Returns:
            Объект модели или None, если не найдено

        Raises:
            ValueError: Если найдено больше одного объекта
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        instances = list(result.scalars().all())

        if len(instances) == 0:
            return None

        if len(instances) > 1:
            raise ValueError(f"Найдено больше одного объекта с id={id}")

        return instances[0]

    async def get_by_id(self, id: int) -> Any | None:
        """
        Получить запись по ID.

        Возвращает Pydantic схему через Data Mapper паттерн.
        Метод _to_schema должен быть переопределен в дочернем классе.

        Args:
            id: ID записи

        Returns:
            Pydantic схема или None, если не найдено

        Raises:
            NotImplementedError: Если метод _to_schema не переопределен
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        orm_obj = result.scalar_one_or_none()

        if orm_obj is None:
            return None

        return self._to_schema(orm_obj)

    async def get_all(self) -> list[Any]:
        """
        Получить все записи.

        Возвращает список Pydantic схем через Data Mapper паттерн.
        Метод _to_schema должен быть переопределен в дочернем классе.

        Returns:
            Список Pydantic схем

        Raises:
            NotImplementedError: Если метод _to_schema не переопределен
        """
        query = select(self.model)
        result = await self.session.execute(query)
        orm_objs = list(result.scalars().all())

        return [self._to_schema(obj) for obj in orm_objs]

    async def edit(self, id: int, **kwargs: Any) -> Any | None:
        """
        Изменить запись по ID.

        Проверяет, что объект существует и что он ровно один.
        Возвращает Pydantic схему через Data Mapper паттерн.

        Args:
            id: ID записи для изменения
            **kwargs: Поля для обновления

        Returns:
            Измененная Pydantic схема или None, если не найдено

        Raises:
            ValueError: Если найдено больше одного объекта (не должно происходить для ID)
            NotImplementedError: Если метод _to_schema не переопределен
        """
        instance = await self._get_one_by_id_exact(id)

        if instance is None:
            return None

        for key, value in kwargs.items():
            setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)

        return self._to_schema(instance)

    async def update(self, id: int, **kwargs: Any) -> Any | None:
        """
        Обновить запись по ID (алиас для edit).

        Args:
            id: ID записи для обновления
            **kwargs: Поля для обновления

        Returns:
            Обновленная Pydantic схема или None, если не найдено
        """
        return await self.edit(id, **kwargs)

    async def delete(self, id: int) -> bool:
        """
        Удалить запись по ID.

        Проверяет, что объект существует и что он ровно один.

        Args:
            id: ID записи для удаления

        Returns:
            True если запись была удалена, False если не найдено

        Raises:
            ValueError: Если найдено больше одного объекта (не должно происходить для ID)
        """
        instance = await self._get_one_by_id_exact(id)

        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def exists(self, id: int) -> bool:
        """
        Проверить существование записи по ID.

        Args:
            id: ID записи

        Returns:
            True если запись существует, False иначе
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
