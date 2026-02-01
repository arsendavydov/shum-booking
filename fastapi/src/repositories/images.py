from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.images import ImagesOrm
from src.repositories.base import BaseRepository
from src.schemas.images import SchemaImage


class ImagesRepository(BaseRepository[ImagesOrm]):
    """
    Репозиторий для работы с изображениями.

    Наследует базовые CRUD методы и добавляет специфичные методы
    для работы с изображениями.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория изображений.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, ImagesOrm)

    def _to_schema(self, orm_obj: ImagesOrm) -> SchemaImage:
        """
        Преобразовать ORM объект изображения в Pydantic схему.

        Args:
            orm_obj: ORM объект изображения

        Returns:
            Pydantic схема SchemaImage
        """
        return SchemaImage(
            id=orm_obj.id,
            filename=orm_obj.filename,
            original_filename=orm_obj.original_filename,
            width=orm_obj.width,
            height=orm_obj.height,
        )

    async def get_by_hotel_id(self, hotel_id: int) -> list[SchemaImage]:
        """
        Получить все изображения отеля.

        Args:
            hotel_id: ID отеля

        Returns:
            Список изображений отеля
        """
        from src.models.images import hotels_images

        query = select(ImagesOrm).join(hotels_images).where(hotels_images.c.hotel_id == hotel_id)
        result = await self.session.execute(query)
        orm_objs = list(result.scalars().unique().all())

        return [self._to_schema(obj) for obj in orm_objs]

    async def link_to_hotel(self, image_id: int, hotel_id: int) -> None:
        """
        Связать изображение с отелем.

        Args:
            image_id: ID изображения
            hotel_id: ID отеля
        """
        from src.models.hotels import HotelsOrm

        # Получаем объекты
        image = await self.session.get(ImagesOrm, image_id)
        hotel = await self.session.get(HotelsOrm, hotel_id)

        if image and hotel:
            # Добавляем связь
            if hotel not in image.hotels:
                image.hotels.append(hotel)
                await self.session.flush()
