from datetime import date, datetime

from pydantic import BaseModel, Field


class Booking(BaseModel):
    """Модель бронирования для создания (POST)."""

    room_id: int = Field(..., description="ID номера")
    date_from: date = Field(..., description="Дата заезда")
    date_to: date = Field(..., description="Дата выезда")


class SchemaBooking(BaseModel):
    """Модель ответа для GET запросов."""

    id: int
    room_id: int
    user_id: int
    date_from: date
    date_to: date
    price: int
    created_at: datetime = Field(..., description="Дата и время создания бронирования")
