from celery import Task
from PIL import Image
import os
import asyncio
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Импортируем celery_app - он должен быть инициализирован до импорта tasks
from src.tasks.celery_app import celery_app

# Импортируем все модели для правильной инициализации SQLAlchemy relationships
from src.models import ImagesOrm, hotels_images, HotelsOrm, CitiesOrm, CountriesOrm
from src.base import Base

# Путь к папке с изображениями
IMAGES_DIR = Path(__file__).resolve().parent.parent / "static" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Разрешения для ресайза
RESIZE_WIDTHS = [200, 500, 1000]

# Получаем настройки БД из переменных окружения напрямую
# Это позволяет Celery работать с разными БД (booking, test) в зависимости от окружения
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'booking')
DB_USERNAME = os.getenv('DB_USERNAME', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

def get_db_session(db_name: str):
    """Создать синхронную сессию БД на основе переданного db_name."""
    if not db_name:
        raise ValueError("db_name обязателен для создания сессии БД")
    db_url = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{db_name}"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(bind=True, name='process_image')
def process_image(self: Task, hotel_id: int, original_filename: str, temp_file_path: str, db_name: str) -> dict:
    """
    Обработка изображения: проверка размера, создание записи в БД, ресайз и сохранение.
    
    Args:
        hotel_id: ID отеля
        original_filename: Оригинальное имя файла
        temp_file_path: Путь к временному файлу
        
    Returns:
        Словарь с результатом обработки
    """
    try:
        # Открываем изображение
        with Image.open(temp_file_path) as img:
            width, height = img.size
            
            # Проверяем минимальную ширину
            if width < 1000:
                # Удаляем временный файл
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                return {
                    'status': 'error',
                    'message': f'Изображение должно быть не менее 1000px в ширину. Текущая ширина: {width}px'
                }
            
            # Создаем запись в БД и связываем с отелем (синхронно)
            image_id = _create_image_in_db_sync(hotel_id, original_filename, width, height, db_name)
            
            if image_id is None:
                # Удаляем временный файл
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                return {
                    'status': 'error',
                    'message': 'Ошибка при создании записи в БД: отель не найден или другая ошибка'
                }
            
            # Создаем ресайзы
            saved_files = []
            for resize_width in RESIZE_WIDTHS:
                # Вычисляем новую высоту с сохранением пропорций
                aspect_ratio = height / width
                resize_height = int(resize_width * aspect_ratio)
                
                # Ресайзим изображение
                resized_img = img.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
                
                # Сохраняем ресайз
                resized_filename = f"{image_id}_{resize_width}w_{original_filename}"
                resized_path = IMAGES_DIR / resized_filename
                resized_img.save(resized_path)
                saved_files.append(str(resized_path))
            
            # Удаляем временный файл
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            return {
                'status': 'success',
                'message': 'Изображение успешно обработано',
                'image_id': image_id,
                'files': saved_files,
                'width': width,
                'height': height
            }
    
    except Exception as e:
        # Удаляем временный файл в случае ошибки
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f'Ошибка при обработке изображения: {str(e)}'
        }


def _create_image_in_db_sync(hotel_id: int, original_filename: str, width: int, height: int, db_name: str) -> int | None:
    """Создать запись изображения в БД и связать с отелем (синхронно)."""
    session = get_db_session(db_name)
    try:
        # Проверяем существование отеля
        hotel = session.query(HotelsOrm).filter(HotelsOrm.id == hotel_id).first()
        if hotel is None:
            print(f"Отель с ID {hotel_id} не найден в БД")
            return None
        
        # Создаем запись изображения
        image = ImagesOrm(
            filename=original_filename,
            original_filename=original_filename,
            width=width,
            height=height
        )
        session.add(image)
        session.flush()  # Получаем ID изображения
        
        # Связываем изображение с отелем
        image.hotels.append(hotel)
        session.commit()
        
        print(f"Создано изображение с ID {image.id} для отеля {hotel_id}")
        return image.id
    except Exception as e:
        session.rollback()
        import traceback
        print(f"Ошибка при создании записи в БД: {e}")
        traceback.print_exc()
        return None
    finally:
        session.close()
