from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base import Base

if TYPE_CHECKING:
    from src.models.countries import CountriesOrm
    from src.models.hotels import HotelsOrm


class CitiesOrm(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    country_id: Mapped[int] = mapped_column(Integer, ForeignKey("countries.id", ondelete="CASCADE"))

    country: Mapped["CountriesOrm"] = relationship("CountriesOrm", back_populates="cities")
    hotels: Mapped[list["HotelsOrm"]] = relationship("HotelsOrm", back_populates="city")
