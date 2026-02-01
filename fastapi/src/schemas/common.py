from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Модель ответа для POST, PUT, PATCH, DELETE запросов."""

    status: str = Field(..., description="Статус операции")
