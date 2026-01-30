# Экспорт зависимостей (импортируем первыми, чтобы избежать циклических импортов)
from src.api.dependencies import (
    DBDep,
    PaginationDep,
    CurrentUserDep,
    AuthServiceDep
)

# Экспорт утилит
from src.api.utils import get_or_404, invalidate_cache, handle_delete_operation, validate_city_by_name

# Экспорт роутеров (импортируем после зависимостей)
from src.api.hotels import router as hotels_router
from src.api.auth import router as auth_router
from src.api.users import router as users_router
from src.api.rooms import router as rooms_router
from src.api.bookings import router as bookings_router
from src.api.facilities import router as facilities_router
from src.api.images import router as images_router
from src.api.countries import router as countries_router
from src.api.cities import router as cities_router

__all__ = [
    # Роутеры
    "hotels_router",
    "auth_router",
    "users_router",
    "rooms_router",
    "bookings_router",
    "facilities_router",
    "images_router",
    "countries_router",
    "cities_router",
    # Зависимости
    "DBDep",
    "PaginationDep",
    "CurrentUserDep",
    "AuthServiceDep",
    # Утилиты
    "get_or_404",
    "invalidate_cache",
    "handle_delete_operation",
    "validate_city_by_name"
]
