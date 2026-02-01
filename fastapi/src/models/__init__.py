# Экспорт всех моделей для удобного импорта
from src.models.bookings import BookingsOrm
from src.models.cities import CitiesOrm
from src.models.countries import CountriesOrm
from src.models.facilities import FacilitiesOrm
from src.models.hotels import HotelsOrm
from src.models.images import ImagesOrm, hotels_images
from src.models.rooms import RoomsOrm
from src.models.users import UsersOrm

__all__ = [
    "BookingsOrm",
    "CitiesOrm",
    "CountriesOrm",
    "FacilitiesOrm",
    "HotelsOrm",
    "ImagesOrm",
    "RoomsOrm",
    "UsersOrm",
    "hotels_images",
]
