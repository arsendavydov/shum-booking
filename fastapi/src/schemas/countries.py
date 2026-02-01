from pydantic import BaseModel, Field


class Country(BaseModel):
    """Модель страны для создания (POST) и полного обновления (PUT)."""

    name: str = Field(..., max_length=100, description="Название страны")
    iso_code: str = Field(..., max_length=2, min_length=2, description="ISO 3166-1 alpha-2 код страны (2 буквы)")


class CountryPATCH(BaseModel):
    """Модель для частичного обновления страны."""

    name: str | None = Field(None, max_length=100, description="Название страны (опционально)")
    iso_code: str | None = Field(
        None, max_length=2, min_length=2, description="ISO 3166-1 alpha-2 код страны (опционально)"
    )


class SchemaCountry(BaseModel):
    """Модель ответа для GET запросов."""

    id: int
    name: str
    iso_code: str

    model_config = {"from_attributes": True}
