from pydantic import BaseModel, ConfigDict, Field

from src.schemas.facilities import SchemaFacility


class Room(BaseModel):
    """Модель комнаты для создания (POST) и полного обновления (PUT)."""

    title: str = Field(..., max_length=100, description="Название комнаты")
    description: str | None = Field(None, description="Описание комнаты (опционально)")
    price: int = Field(..., ge=0, description="Цена за ночь")
    quantity: int = Field(..., ge=0, description="Количество комнат")
    facility_ids: list[int] | None = Field(None, description="Список ID удобств для добавления к комнате (опционально)")


class RoomPATCH(BaseModel):
    """Модель для частичного обновления комнаты."""

    title: str | None = Field(None, max_length=100, description="Название комнаты (опционально)")
    description: str | None = Field(None, description="Описание комнаты (опционально)")
    price: int | None = Field(None, ge=0, description="Цена за ночь (опционально)")
    quantity: int | None = Field(None, ge=0, description="Количество комнат (опционально)")
    facility_ids: list[int] | None = Field(None, description="Список ID удобств для замены (опционально)")


class SchemaRoom(BaseModel):
    """Модель ответа для GET запросов."""

    id: int = Field(..., description="ID комнаты")
    hotel_id: int = Field(..., description="ID отеля")
    title: str = Field(..., max_length=100, description="Название комнаты")
    description: str | None = Field(None, description="Описание комнаты")
    price: int = Field(..., ge=0, description="Цена за ночь")
    quantity: int = Field(..., ge=0, description="Количество комнат")
    facilities: list[SchemaFacility] = Field(default_factory=list, description="Список удобств комнаты")
    model_config = ConfigDict(from_attributes=True)


class SchemaRoomAvailable(BaseModel):
    """Модель ответа для GET запросов доступных номеров."""

    id: int = Field(..., description="ID комнаты")
    hotel_id: int = Field(..., description="ID отеля")
    title: str = Field(..., max_length=100, description="Название комнаты")
    description: str | None = Field(None, description="Описание комнаты")
    price: int = Field(..., ge=0, description="Цена за ночь")
    quantity: int = Field(..., ge=0, description="Количество свободных комнат на указанный период")
    facilities: list[SchemaFacility] = Field(default_factory=list, description="Список удобств комнаты")
    model_config = ConfigDict(from_attributes=True)
