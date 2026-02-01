from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base import Base

if TYPE_CHECKING:
    from src.models.rooms import RoomsOrm

# Промежуточная таблица для many-to-many связи между rooms и facilities
rooms_facilities = Table(
    "rooms_facilities",
    Base.metadata,
    Column("room_id", Integer, ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
    Column("facility_id", Integer, ForeignKey("facilities.id", ondelete="CASCADE"), primary_key=True),
)


class FacilitiesOrm(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100))

    # Many-to-many связь с rooms через промежуточную таблицу
    rooms: Mapped[list["RoomsOrm"]] = relationship("RoomsOrm", secondary=rooms_facilities, back_populates="facilities")
