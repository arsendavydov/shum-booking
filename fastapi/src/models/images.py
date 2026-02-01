from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base import Base

if TYPE_CHECKING:
    from src.models.hotels import HotelsOrm

# Промежуточная таблица для many-to-many связи между hotels и images
hotels_images = Table(
    "hotels_images",
    Base.metadata,
    Column("hotel_id", Integer, ForeignKey("hotels.id", ondelete="CASCADE"), primary_key=True),
    Column("image_id", Integer, ForeignKey("images.id", ondelete="CASCADE"), primary_key=True),
)


class ImagesOrm(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)

    # Many-to-many связь с hotels через промежуточную таблицу
    hotels: Mapped[list["HotelsOrm"]] = relationship("HotelsOrm", secondary=hotels_images, back_populates="images")
