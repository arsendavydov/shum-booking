import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Path as PathParam, UploadFile
from PIL import Image as PILImage

from src.api.dependencies import ImagesServiceDep
from src.config import settings
from src.schemas import MessageResponse
from src.schemas.images import ImageUploadResponse, SchemaImage
from src.services.images import ImagesService
from src.tasks.tasks import process_image
from src.utils.db_manager import DBManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Путь к папке с изображениями
IMAGES_DIR = Path(__file__).resolve().parent.parent / "static" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/upload/{hotel_id}",
    summary="Загрузить изображение для отеля",
    description="Загружает изображение для отеля. Файл должен быть не менее 1000px в ширину. Изображение обрабатывается в фоне через Celery: создаются версии 200px, 500px и 1000px в ширину.",
    response_model=ImageUploadResponse,
)
async def upload_image(
    hotel_id: int = PathParam(..., description="ID отеля"), file: UploadFile = File(..., description="Файл изображения")
) -> ImageUploadResponse:
    """
    Загрузить изображение для отеля.

    Изображение обрабатывается асинхронно через Celery:
    - Проверяется минимальная ширина (1000px)
    - Создаются версии 200px, 500px, 1000px в ширину
    - Сохраняются в папку static/images

    Args:
        hotel_id: ID отеля
        file: Файл изображения
        db: Сессия базы данных

    Returns:
        Информация о загруженном изображении

    Raises:
        HTTPException: 404 если отель не найден
        HTTPException: 400 если файл не является изображением или слишком маленький
    """
    # Проверяем тип файла
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")

    # Проверяем существование отеля перед сохранением файла
    async with DBManager() as db:
        images_service = ImagesService(db)
        await images_service.validate_hotel_exists(hotel_id)

    # Сохраняем файл и проверяем размер синхронно в отдельном потоке ДО запуска Celery задачи
    # Это позволяет вернуть ошибку 400 сразу, если изображение слишком маленькое
    def save_and_check_image(file_content: bytes, file_suffix: str) -> tuple[str, int, int]:
        """Сохранить файл и проверить размер изображения синхронно в отдельном потоке."""
        temp_dir = Path(__file__).resolve().parent.parent / "static" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        import uuid

        temp_filename = f"{uuid.uuid4()}{file_suffix}"
        temp_file_path = str(temp_dir / temp_filename)

        # Сохраняем файл
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)

        # Проверяем размер изображения
        with PILImage.open(temp_file_path) as img:
            width, height = img.size

        return temp_file_path, width, height

    # Читаем файл
    content = await file.read()

    # Ограничиваем максимальный размер файла (в байтах)
    max_size_mb = settings.MAX_IMAGE_FILE_SIZE_MB
    max_size_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Размер файла превышает допустимый лимит {max_size_mb} МБ",
        )

    # Выполняем проверку размеров изображения в отдельном потоке
    temp_file_path, width, _height = await asyncio.to_thread(
        save_and_check_image, content, os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    )

    # Проверяем минимальную ширину ДО запуска Celery задачи
    if width < 1000:
        os.remove(temp_file_path)
        raise HTTPException(
            status_code=400, detail=f"Изображение должно быть не менее 1000px в ширину. Текущая ширина: {width}px"
        )

    try:
        # Запускаем обработку в фоне через Celery
        # Celery задача создаст запись в БД, проверит размер, создаст ресайзы
        # Передаем DB_NAME, чтобы Celery мог подключиться к правильной БД (booking или test)
        task = process_image.delay(
            hotel_id=hotel_id,
            original_filename=file.filename or "image.jpg",
            temp_file_path=temp_file_path,
            db_name=settings.DB_NAME,
        )

        # Ждем завершения задачи для получения image_id
        # В production можно вернуть task.id и проверять статус через отдельный endpoint
        try:
            result = task.get(timeout=30)  # Ждем до 30 секунд
            if result.get("status") == "success":
                image_id = result.get("image_id", 0)
                return ImageUploadResponse(status="OK", image_id=image_id, message="Изображение загружено и обработано")
            else:
                # Если обработка не удалась, удаляем временный файл
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                raise HTTPException(status_code=400, detail=result.get("message", "Ошибка при обработке изображения"))
        except Exception as e:
            # Если задача не завершилась или произошла ошибка
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise HTTPException(status_code=500, detail=f"Ошибка при обработке изображения: {e!s}")

    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке изображения: {e!s}")


@router.get(
    "/hotel/{hotel_id}",
    summary="Получить изображения отеля",
    description="Возвращает список всех изображений указанного отеля",
    response_model=list[SchemaImage],
)
async def get_hotel_images(
    images_service: ImagesServiceDep,
    hotel_id: int = PathParam(..., description="ID отеля"),
) -> list[SchemaImage]:
    """
    Получить список изображений отеля.

    Args:
        hotel_id: ID отеля
        images_service: Сервис для работы с изображениями

    Returns:
        Список изображений отеля

    Raises:
        HTTPException: 404 если отель не найден
    """
    # Проверяем существование отеля
    try:
        await images_service.validate_hotel_exists(hotel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Получаем изображения
    images = await images_service.images_repo.get_by_hotel_id(hotel_id)

    return images


@router.delete(
    "/{image_id}",
    summary="Удалить изображение",
    description="Удаляет изображение по указанному ID. Также удаляет все файлы ресайзов (200px, 500px, 1000px) с диска. Возвращает статус 'OK' при успешном удалении.",
    response_model=MessageResponse,
)
async def delete_image(
    images_service: ImagesServiceDep,
    image_id: int = PathParam(..., description="ID изображения"),
) -> MessageResponse:
    """
    Удалить изображение.
    Удаляет запись из БД и все файлы ресайзов с диска.

    Args:
        image_id: ID изображения для удаления
        images_service: Сервис для работы с изображениями

    Returns:
        Словарь со статусом операции {"status": "OK"}

    Raises:
        HTTPException: 404 если изображение с указанным ID не найдено
    """
    async with DBManager.transaction(images_service.session):
        deleted = await images_service.delete_image(image_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Изображение не найдено")

    return MessageResponse(status="OK")
