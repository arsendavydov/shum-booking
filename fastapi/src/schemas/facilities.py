from pydantic import BaseModel, ConfigDict, Field


class Facility(BaseModel):
    """Модель удобства для создания (POST)."""

    title: str = Field(..., max_length=100, description="Название удобства")


class SchemaFacility(BaseModel):
    """Модель ответа для GET запросов."""

    id: int = Field(..., description="ID удобства")
    title: str = Field(..., max_length=100, description="Название удобства")
    model_config = ConfigDict(from_attributes=True)
