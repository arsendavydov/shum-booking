from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base import Base

if TYPE_CHECKING:
    from src.models.cities import CitiesOrm


class CountriesOrm(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    iso_code: Mapped[str] = mapped_column(String(2), unique=True)

    cities: Mapped[list["CitiesOrm"]] = relationship("CitiesOrm", back_populates="country")
