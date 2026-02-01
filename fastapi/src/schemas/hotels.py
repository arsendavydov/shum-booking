from datetime import time

from pydantic import BaseModel, Field

from src.schemas.rooms import SchemaRoomAvailable


class Hotel(BaseModel):
    """Модель отеля для создания (POST) и полного обновления (PUT)."""

    title: str = Field(..., max_length=100, description="Название отеля")
    city: str = Field(..., description="Название города (без учета регистра, обязательно)")
    address: str = Field(..., description="Адрес отеля (улица и номер)")
    postal_code: str | None = Field(None, max_length=20, description="Почтовый индекс (опционально)")
    check_in_time: time | None = Field(default=time(14, 0), description="Время заезда (по умолчанию 14:00)")
    check_out_time: time | None = Field(default=time(12, 0), description="Время выезда (по умолчанию 12:00)")


class HotelPATCH(BaseModel):
    """Модель для частичного обновления отеля."""

    title: str | None = Field(None, max_length=100, description="Название отеля (опционально)")
    city: str | None = Field(None, description="Название города (без учета регистра, опционально)")
    address: str | None = Field(None, description="Адрес отеля (опционально)")
    postal_code: str | None = Field(None, max_length=20, description="Почтовый индекс (опционально)")
    check_in_time: time | None = Field(None, description="Время заезда (опционально)")
    check_out_time: time | None = Field(None, description="Время выезда (опционально)")


class SchemaHotel(BaseModel):
    """Модель ответа для GET запросов."""

    id: int
    title: str
    address: str
    postal_code: str | None = None
    check_in_time: time | None = None
    check_out_time: time | None = None
    city: str | None = None
    country: str | None = None

    model_config = {"from_attributes": True}


class SchemaHotelWithRooms(BaseModel):
    """Модель ответа для GET запросов отелей с доступными комнатами."""

    id: int
    title: str
    address: str
    postal_code: str | None = None
    check_in_time: time | None = None
    check_out_time: time | None = None
    city: str | None = None
    country: str | None = None
    rooms: list[SchemaRoomAvailable] = Field(
        default_factory=list, description="Список комнат с актуальным количеством свободных номеров"
    )

    model_config = {"from_attributes": True}
