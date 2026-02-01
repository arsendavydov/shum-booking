from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from src.api import (
    hotels_router,
    auth_router,
    users_router,
    rooms_router,
    bookings_router,
    facilities_router,
    images_router,
    countries_router,
    cities_router
)
from src.config import settings
from src.utils.logger import setup_logging
from src.utils.startup import startup_handler, shutdown_handler
from src.middleware.http_logging import HTTPLoggingMiddleware

log_file_name = "app_test.log" if settings.DB_NAME == "test" else "app.log"
setup_logging(log_file_name=log_file_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan события для FastAPI - выполняется при старте и остановке приложения."""
    await startup_handler()
    yield
    await shutdown_handler()


app = FastAPI(lifespan=lifespan)

if settings.DB_NAME != "test":
    app.add_middleware(HTTPLoggingMiddleware)

app.include_router(auth_router, prefix="/auth", tags=["Аутентификация"])
app.include_router(users_router, prefix="/users", tags=["Пользователи"])
app.include_router(hotels_router, prefix="/hotels", tags=["Отели"])
app.include_router(rooms_router, prefix="/hotels/{hotel_id}/rooms", tags=["Номера"])
app.include_router(bookings_router, prefix="/bookings", tags=["Бронирования"])
app.include_router(facilities_router, prefix="/facilities", tags=["Удобства"])
app.include_router(images_router, prefix="/images", tags=["Изображения отелей"])
app.include_router(countries_router, prefix="/countries", tags=["Страны"])
app.include_router(cities_router, prefix="/cities", tags=["Города"])

if __name__ == "__main__":
    uvicorn.run(app="src.main:app", host="127.0.0.1", port=8000, reload=True)
