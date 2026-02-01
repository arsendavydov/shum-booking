# Экспорт зависимостей (импортируем первыми, чтобы избежать циклических импортов)
from src.api.dependencies import AuthServiceDep, CurrentUserDep, DBDep, PaginationDep

# Экспорт роутеров (импортируем после зависимостей)
from src.api.auth import router as auth_router
from src.api.bookings import router as bookings_router
from src.api.cities import router as cities_router
from src.api.countries import router as countries_router
from src.api.facilities import router as facilities_router
from src.api.hotels import router as hotels_router
from src.api.images import router as images_router
from src.api.rooms import router as rooms_router
from src.api.users import router as users_router

# Экспорт утилит
from src.utils.api_helpers import (
    get_or_404,
    handle_delete_operation,
    handle_validation_error,
    invalidate_cache,
    validate_entity_exists,
)

__all__ = [
    "AuthServiceDep",
    "CurrentUserDep",
    "DBDep",
    "PaginationDep",
    "auth_router",
    "bookings_router",
    "cities_router",
    "countries_router",
    "facilities_router",
    "get_or_404",
    "handle_delete_operation",
    "handle_validation_error",
    "hotels_router",
    "images_router",
    "invalidate_cache",
    "rooms_router",
    "users_router",
    "validate_entity_exists",
]
