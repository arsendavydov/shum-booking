from datetime import time as dt_time
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base import Base

if TYPE_CHECKING:
    from src.models.cities import CitiesOrm
    from src.models.images import ImagesOrm


class HotelsOrm(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    city_id: Mapped[int] = mapped_column(Integer, ForeignKey("cities.id", ondelete="CASCADE"))
    address: Mapped[str] = mapped_column(Text)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    check_in_time: Mapped[dt_time | None] = mapped_column(Time, nullable=True)
    check_out_time: Mapped[dt_time | None] = mapped_column(Time, nullable=True)

    city: Mapped["CitiesOrm"] = relationship("CitiesOrm", back_populates="hotels")

    # Many-to-many связь с images через промежуточную таблицу
    images: Mapped[list["ImagesOrm"]] = relationship("ImagesOrm", secondary="hotels_images", back_populates="hotels")
