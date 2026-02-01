from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base import Base

if TYPE_CHECKING:
    from src.models.rooms import RoomsOrm


class BookingsOrm(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    date_from: Mapped[Date] = mapped_column(Date)
    date_to: Mapped[Date] = mapped_column(Date)
    price: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")

    room: Mapped["RoomsOrm"] = relationship("RoomsOrm")

    @hybrid_property
    def total_cost(self) -> int:
        """
        Вычисляемое свойство для расчета общей стоимости бронирования.

        Использует цену номера за ночь и количество ночей.
        Может использоваться как в Python коде, так и в SQL запросах.

        Returns:
            Общая стоимость бронирования (цена за ночь * количество ночей)
        """
        if self.room is None:
            # Если relationship не загружен, используем сохраненное значение price
            return self.price
        nights = (self.date_to - self.date_from).days
        return self.room.price * nights

    @staticmethod
    def calculate_total_price(room_price_per_night: int, date_from: Date, date_to: Date) -> int:
        """
        Рассчитать общую цену бронирования на основе цены номера за ночь и дат.

        Args:
            room_price_per_night: Цена номера за одну ночь
            date_from: Дата заезда
            date_to: Дата выезда

        Returns:
            Общая цена бронирования (цена за ночь * количество ночей)

        Raises:
            ValueError: Если количество ночей <= 0
        """
        nights = (date_to - date_from).days
        if nights <= 0:
            raise ValueError("Количество ночей должно быть больше нуля")
        return room_price_per_night * nights
