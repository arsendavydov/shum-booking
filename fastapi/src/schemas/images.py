from pydantic import BaseModel, ConfigDict


class ImageBase(BaseModel):
    filename: str
    original_filename: str
    width: int
    height: int


class Image(ImageBase):
    pass


class SchemaImage(BaseModel):
    """Модель ответа для GET запросов изображений."""

    id: int
    filename: str
    original_filename: str
    width: int
    height: int

    model_config = ConfigDict(from_attributes=True)


class ImageUploadResponse(BaseModel):
    """Модель ответа для POST запросов загрузки изображений."""

    status: str
    image_id: int
    message: str
