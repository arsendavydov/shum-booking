from pydantic import BaseModel, Field

from src.schemas.countries import SchemaCountry


class City(BaseModel):
    """Модель города для создания (POST) и полного обновления (PUT)."""

    name: str = Field(..., max_length=100, description="Название города")
    country_id: int = Field(..., description="ID страны")


class CityPATCH(BaseModel):
    """Модель для частичного обновления города."""

    name: str | None = Field(None, max_length=100, description="Название города (опционально)")
    country_id: int | None = Field(None, description="ID страны (опционально)")


class SchemaCity(BaseModel):
    """Модель ответа для GET запросов."""

    id: int
    name: str
    country: SchemaCountry | None = None

    model_config = {"from_attributes": True}

