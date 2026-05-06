# FastAPI приложение - Shum Booking

Основной модуль проекта - FastAPI приложение для сервиса бронирования отелей.

**🌐 Production:** https://async-black.ru/apps/shum-booking/docs

---

## 📁 Структура проекта

```
fastapi/
├── src/                    # Исходный код приложения
│   ├── api/               # API endpoints (FastAPI роутеры)
│   │   ├── auth.py        # Аутентификация и авторизация
│   │   ├── bookings.py    # Бронирования
│   │   ├── cities.py      # Города
│   │   ├── countries.py   # Страны
│   │   ├── facilities.py  # Удобства
│   │   ├── health.py      # Health checks и метрики
│   │   ├── hotels.py      # Отели
│   │   ├── images.py      # Изображения
│   │   ├── rooms.py       # Номера
│   │   └── users.py       # Пользователи
│   ├── services/          # Бизнес-логика (Service Layer)
│   ├── repositories/      # Работа с БД (Repository Layer + Data Mapper)
│   │   └── mappers/       # Data Mapper для преобразования ORM -> Schema
│   ├── models/            # SQLAlchemy ORM модели
│   ├── schemas/           # Pydantic схемы (DTO)
│   ├── middleware/        # Middleware (rate limiting, logging, exception handling)
│   ├── metrics/           # Prometheus метрики
│   ├── connectors/        # Подключения (Redis)
│   ├── exceptions/        # Кастомные исключения
│   ├── utils/             # Утилиты (logger, db_manager, startup)
│   ├── tasks/             # Celery задачи
│   ├── migrations/        # Alembic миграции
│   └── main.py            # Точка входа FastAPI приложения
├── tests/                 # Тесты
│   ├── unit_tests/        # Unit-тесты (сервисы, репозитории)
│   ├── api_tests/         # API-тесты (эндпоинты)
│   ├── database_tests/    # Тесты БД (индексы)
│   └── load_tests/        # Нагрузочные тесты (Locust)
├── scripts/               # Вспомогательные скрипты
│   └── lint.sh            # Линтинг и проверка типов
├── requirements.txt       # Python зависимости
├── pyproject.toml         # Конфигурация Ruff и Pyright
├── pytest.ini             # Конфигурация Pytest
└── alembic.ini            # Конфигурация Alembic
```

---

## 🏗️ Архитектура слоев

Приложение использует **слоистую архитектуру** с четким разделением ответственности:

```
HTTP Request
    ↓
API Layer (api/*.py)
    ↓
Service Layer (services/*.py) - бизнес-логика
    ↓
Repository Layer (repositories/*.py) - работа с БД
    ↓
Data Mapper (repositories/mappers/*.py) - ORM -> Schema
    ↓
ORM Models (models/*.py) - SQLAlchemy
    ↓
PostgreSQL
```

**Ключевые принципы:**
- **API Layer** - только валидация запросов и формирование ответов
- **Service Layer** - вся бизнес-логика, не зависит от БД
- **Repository Layer** - абстракция над БД, использует Data Mapper для преобразования
- **Data Mapper** - преобразует ORM объекты в Pydantic схемы (не используется `from_attributes=True` напрямую)

Детальная схема потока данных описана в [`ARCHITECTURE.md`](../ARCHITECTURE.md).

---

## 🚀 Быстрый старт

### Требования

- **Python 3.11**
- **PostgreSQL 16** (локально или в Docker)
- **Redis 7** (локально или в Docker)
- **Poetry** или **pip** для управления зависимостями

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка окружения

Создай файл `.env` в корне проекта:

```bash

cp .local.env.template .local.env
```

Минимально необходимые переменные:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`
- `JWT_SECRET_KEY` 
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_AUTH_PER_MINUTE`

### 3. Запуск локально (без Docker)

**Важно:** Убедись, что PostgreSQL и Redis запущены локально или в Docker.

```bash
cd fastapi

# Применить миграции (если БД пустая)
alembic upgrade head

# Запустить приложение
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Или через `main.py`:

```bash
python src/main.py
```

Приложение будет доступно:
- **API:** http://127.0.0.1:8000
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

---

## 🧪 Тестирование

### Запуск тестов

#### Unit-тесты (без зависимостей от БД)

```bash
pytest tests/unit_tests/ -v
```

#### API-тесты (требуют запущенное приложение)

```bash
pytest tests/api_tests/ -v
```

#### E2E тесты (End-to-End)

```bash
# Локальное тестирование (localhost:8001)
pytest tests/e2e_tests/ -v

# Тестирование production сервера
E2E_BASE_URL=https://async-black.ru/apps/shum-booking pytest tests/e2e_tests/ -v

# Изменить задержку между запросами (по умолчанию 0.1s)
E2E_REQUEST_DELAY=0.2 pytest tests/e2e_tests/ -v
```

**Важно:** E2E тесты требуют запущенное приложение. Они проверяют полные пользовательские сценарии:
- Полный цикл бронирования (регистрация -> поиск -> бронирование -> отмена)
- Полный цикл аутентификации (регистрация -> вход -> обновление токена -> выход)
- Полный цикл поиска отеля (страна -> город -> отель -> номера)

#### Все тесты

```bash
pytest tests/ -v
```

#### Быстрый запуск (через скрипт)

Из корня проекта:

```bash
# Полный набор тестов (с нагрузочным тестированием)
./fastapi/tests/run_tests.sh

# Быстрые тесты (без нагрузочного тестирования)
./fastapi/tests/run_tests_quick.sh

# Только нагрузочные тесты
./fastapi/tests/run_load_tests.sh
```

### Типы тестов

- **`tests/unit_tests/`** - unit-тесты для сервисов и репозиториев (с моками)
- **`tests/api_tests/`** - интеграционные тесты для API эндпоинтов
- **`tests/e2e_tests/`** - E2E тесты (End-to-End) для полных пользовательских сценариев
- **`tests/database_tests/`** - тесты для проверки индексов БД
- **`tests/load_tests/`** - нагрузочные тесты через Locust

### Маркеры pytest

```bash
# Только тесты для отелей
pytest -m hotels

# Только unit-тесты
pytest -m unit

# Только E2E тесты
pytest -m e2e

# Все кроме медленных (E2E, нагрузочные)
pytest -m "not slow"

# Только тесты rate limiting
pytest -m rate_limiting
```

---

## 🔍 Линтинг и проверка типов

### Через скрипт (рекомендуется)

```bash
cd fastapi
./scripts/lint.sh check    # Проверка
./scripts/lint.sh fix      # Исправление и форматирование
```

### Вручную

```bash
cd fastapi

# Ruff (линтер)
ruff check src/ tests/
ruff check --fix src/ tests/        # Автоисправление
ruff format src/ tests/              # Форматирование

# Pyright (проверка типов)
pyright src/
```

---

## 📊 Миграции базы данных

Проект использует **Alembic** для управления миграциями.

### Создание новой миграции

```bash
cd fastapi

# Создать миграцию на основе изменений в моделях
alembic revision --autogenerate -m "Описание изменений"

# Создать пустую миграцию
alembic revision -m "Описание изменений"
```

### Применение миграций

```bash
# Применить все миграции до последней
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Применить конкретную миграцию
alembic upgrade <revision>

# Показать текущую версию
alembic current
```

### История миграций

```bash
# Показать все миграции
alembic history

# Показать текущую версию и историю
alembic current
alembic history --verbose
```

**Важно:** Миграции применяются автоматически при старте приложения в тестовом окружении (`DB_NAME=test`).

---

## 🛠️ Разработка

### Структура кода

При добавлении нового функционала следуй архитектуре:

1. **ORM Model** (`src/models/`) - определи SQLAlchemy модель
2. **Pydantic Schema** (`src/schemas/`) - определи схемы для запросов/ответов
3. **Repository** (`src/repositories/`) - создай репозиторий с методами работы с БД
4. **Data Mapper** (`src/repositories/mappers/`) - создай маппер для преобразования ORM -> Schema
5. **Service** (`src/services/`) - создай сервис с бизнес-логикой
6. **API Router** (`src/api/`) - создай роутер с эндпоинтами
7. **Миграция** (`src/migrations/versions/`) - создай миграцию для изменений в БД

### Пример: добавление нового эндпоинта

```python
# 1. src/api/new_feature.py
from fastapi import APIRouter, Depends
from src.schemas.new_feature import NewFeatureSchema
from src.services.new_feature import NewFeatureService

router = APIRouter(prefix="/new-feature", tags=["New Feature"])

@router.get("/", response_model=NewFeatureSchema)
async def get_new_feature(
    service: NewFeatureService = Depends()
):
    return await service.get_feature()
```

```python
# 2. src/main.py - добавить роутер
from src.api.new_feature import router as new_feature_router

app.include_router(new_feature_router, prefix="/new-feature")
```

### Логирование

Логи пишутся в `fastapi/logs/`:
- `app.log` - основной лог приложения
- `app_test.log` - лог тестового окружения

Настройки логирования в `src/utils/logger.py`.

---

## 📦 Зависимости

Основные зависимости (см. `requirements.txt`):

- **FastAPI** - веб-фреймворк
- **SQLAlchemy** (async) - ORM
- **Alembic** - миграции БД
- **Pydantic** - валидация данных
- **Redis** - кэширование и rate limiting
- **Celery** - фоновые задачи
- **Prometheus Client** - метрики
- **Pytest** - тестирование
- **Ruff** - линтинг
- **Pyright** - проверка типов

---

## 🔗 Полезные ссылки

- **Главный README:** [`../README.md`](../README.md)
- **Архитектура:** [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- **CI/CD:** [`../ci/README.md`](../ci/README.md)
- **Changelog:** [`../CHANGELOG.md`](../CHANGELOG.md)

---

## 🐛 Troubleshooting

### Ошибка подключения к БД

```bash
# Проверь, что PostgreSQL запущен
# Проверь переменные окружения в .env
# Проверь, что миграции применены
alembic upgrade head
```

### Ошибка подключения к Redis

```bash
# Проверь, что Redis запущен
redis-cli ping  # Должен вернуть PONG
```

### Ошибки импорта модулей

```bash
# Убедись, что виртуальное окружение активировано
source venv/bin/activate

# Переустанови зависимости
pip install -r requirements.txt
```

### Тесты не проходят

```bash
# Убедись, что приложение запущено (для API-тестов)
# Проверь, что БД доступна
# Проверь переменные окружения в .test.env
```

---

## 📝 Примечания

- Все пути в коде **относительные** (начинаются с `src/`)
- Переменные окружения загружаются из `.env` файла в корне проекта (на уровень выше `fastapi/`)
- В Docker переменные передаются через `docker-compose.yml` или Kubernetes ConfigMap/Secret
- Логирование настраивается автоматически при старте приложения
- Миграции применяются автоматически в тестовом окружении

