"""
Unit тесты для ImagesService.

Тестируют бизнес-логику сервиса с моками репозиториев.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions.domain import EntityNotFoundError
from src.services.images import ImagesService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Фикстура для создания мока сессии."""
    return AsyncMock()


@pytest.fixture
def images_service(mock_session):
    """Фикстура для создания экземпляра ImagesService."""
    return ImagesService(mock_session)


@pytest.fixture
def mock_images_repo():
    """Фикстура для создания мока репозитория изображений."""
    return AsyncMock()


@pytest.fixture
def mock_hotels_repo():
    """Фикстура для создания мока репозитория отелей."""
    return AsyncMock()


class TestImagesServiceValidateHotelExists:
    """Тесты для проверки существования отеля."""

    @pytest.mark.asyncio
    async def test_validate_hotel_exists_success(self, images_service, mock_hotels_repo):
        """Проверить успешную проверку существования отеля."""
        hotel_id = 1
        from src.schemas.hotels import SchemaHotel

        from src.schemas.hotels import SchemaHotel

        mock_hotels_repo.get_by_id.return_value = SchemaHotel(id=hotel_id, title="Отель", address="Адрес")

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo):
            await images_service.validate_hotel_exists(hotel_id)

        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)

    @pytest.mark.asyncio
    async def test_validate_hotel_exists_not_found(self, images_service, mock_hotels_repo):
        """Проверить, что проверка несуществующего отеля выбрасывает исключение."""
        hotel_id = 999
        mock_hotels_repo.get_by_id.return_value = None

        with patch("src.utils.db_manager.DBManager.get_hotels_repository", return_value=mock_hotels_repo):
            with pytest.raises(EntityNotFoundError) as exc_info:
                await images_service.validate_hotel_exists(hotel_id)

        assert "Отель" in str(exc_info.value)
        mock_hotels_repo.get_by_id.assert_called_once_with(hotel_id)


class TestImagesServiceDeleteImage:
    """Тесты для удаления изображений."""

    @pytest.mark.asyncio
    async def test_delete_image_success(self, images_service, mock_images_repo):
        """Проверить успешное удаление изображения."""
        image_id = 1
        from src.schemas.images import SchemaImage

        image = SchemaImage(id=image_id, filename="test.jpg", original_filename="test.jpg", width=100, height=100)

        mock_images_repo.get_by_id.return_value = image
        mock_images_repo.delete.return_value = True

        with patch("src.utils.db_manager.DBManager.get_images_repository", return_value=mock_images_repo), patch(
            "src.services.images.IMAGES_DIR", Path("/tmp/test_images")
        ), patch("src.services.images.os.remove") as mock_remove, patch(
            "src.services.images.Path.glob", return_value=[]
        ):
            result = await images_service.delete_image(image_id)

        assert result is True
        mock_images_repo.get_by_id.assert_called_once_with(image_id)
        mock_images_repo.delete.assert_called_once_with(image_id)

    @pytest.mark.asyncio
    async def test_delete_image_not_found(self, images_service, mock_images_repo):
        """Проверить удаление несуществующего изображения."""
        image_id = 999
        mock_images_repo.get_by_id.return_value = None

        with patch("src.utils.db_manager.DBManager.get_images_repository", return_value=mock_images_repo):
            result = await images_service.delete_image(image_id)

        assert result is False
        mock_images_repo.get_by_id.assert_called_once_with(image_id)
        mock_images_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_image_removes_files(self, images_service, mock_images_repo):
        """Проверить, что удаление изображения удаляет файлы с диска."""
        image_id = 1
        from src.schemas.images import SchemaImage

        image = SchemaImage(id=image_id, filename="test.jpg", original_filename="test.jpg", width=100, height=100)

        mock_images_repo.get_by_id.return_value = image
        mock_images_repo.delete.return_value = True

        mock_file1 = MagicMock()
        mock_file1.exists.return_value = True
        mock_file2 = MagicMock()
        mock_file2.exists.return_value = True

        with patch("src.utils.db_manager.DBManager.get_images_repository", return_value=mock_images_repo), patch(
            "src.services.images.IMAGES_DIR", Path("/tmp/test_images")
        ), patch("src.services.images.os.remove") as mock_remove, patch(
            "src.services.images.Path.glob", return_value=[mock_file1, mock_file2]
        ):
            result = await images_service.delete_image(image_id)

        assert result is True
        assert mock_remove.call_count >= 2

