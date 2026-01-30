from celery import Celery
import os
from src.utils.logger import setup_logging

# Инициализируем логирование для Celery
# Используем LOG_LEVEL из переменных окружения
log_level = os.getenv('LOG_LEVEL', 'INFO')
setup_logging(log_level=log_level)

# Получаем настройки Redis из переменных окружения напрямую
# Не импортируем settings, чтобы избежать ошибок валидации JWT настроек
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_DB = os.getenv('REDIS_DB', '0')

# Создаем celery_app БЕЗ include, чтобы избежать импорта tasks при инициализации
celery_app = Celery(
    'tasks',
    broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
    backend=f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
)

# Автоматически находим и загружаем задачи из модуля tasks
celery_app.autodiscover_tasks(['src.tasks'], force=True)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)