# Архитектура проекта: Поток данных от API до БД

**Дата обновления:** 3 февраля 2026

## Общая схема потока данных

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HTTP REQUEST (FastAPI)                           │
│                    GET /hotels/{hotel_id}/rooms/{room_id}                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    HTTPLoggingMiddleware                                  │
│                    Логирование всех HTTP запросов                         │
│                    Формат: client_host - "method path protocol" status   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Global Exception Handlers                             │
│                    - DatabaseError → database_exception_handler          │
│                    - Exception → general_exception_handler                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API Layer (api/rooms.py)                         │
│                                                                           │
│  @router.get("/{room_id}")                                               │
│  async def get_room_by_id(                                               │
│      hotel_id: int,                                                      │
│      room_id: int,                                                       │
│      db: DBDep                                                           │
│  ) -> SchemaRoom:                                                        │
│      repo = DBManager.get_rooms_repository(db)                          │
│      room = await get_or_404(repo.get_by_id, room_id, "Номер")          │
│      return room  # Возвращает SchemaRoom                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Pydantic Schemas (schemas/rooms.py)                   │
│                                                                           │
│  class SchemaRoom(BaseModel):                                            │
│      id: int                                                             │
│      hotel_id: int                                                       │
│      title: str                                                          │
│      price: int                                                          │
│      quantity: int                                                        │
│      facilities: List[SchemaFacility]                                    │
│      model_config = ConfigDict(from_attributes=True)                    │
│                                                                           │
│  ⚠️ Схемы НЕ используются напрямую с ORM - только через Data Mapper    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Repository Layer (repositories/rooms.py)                    │
│                    ⭐ DATA MAPPER PATTERN ⭐                             │
│                                                                           │
│  class RoomsRepository(BaseRepository[RoomsOrm]):                       │
│                                                                           │
│      def _to_schema(self, orm_obj: RoomsOrm) -> SchemaRoom:             │
│          """Преобразование ORM → Pydantic через Data Mapper"""          │
│          facilities = self._facilities_to_schema(orm_obj.facilities)    │
│          return SchemaRoom(                                              │
│              id=orm_obj.id,                                              │
│              hotel_id=orm_obj.hotel_id,                                  │
│              title=orm_obj.title,                                         │
│              price=orm_obj.price,                                         │
│              quantity=orm_obj.quantity,                                   │
│              facilities=facilities                                        │
│          )                                                                │
│                                                                           │
│      async def get_by_id(self, id: int) -> Optional[SchemaRoom]:      │
│          query = select(self.model).where(...)                           │
│          result = await self.session.execute(query)                      │
│          orm_obj = result.scalar_one_or_none()                          │
│          return self._to_schema(orm_obj)  # ORM → Schema                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              ORM Models (models/rooms.py)                                │
│                    SQLAlchemy ORM                                        │
│                                                                           │
│  class RoomsOrm(Base):                                                    │
│      __tablename__ = "rooms"                                              │
│                                                                           │
│      id: Mapped[int]                                                      │
│      hotel_id: Mapped[int]                                               │
│      title: Mapped[str]                                                  │
│      price: Mapped[int]                                                   │
│      quantity: Mapped[int]                                                 │
│                                                                           │
│      facilities: Mapped[list["FacilitiesOrm"]] = relationship(            │
│          "FacilitiesOrm",                                                 │
│          secondary="rooms_facilities",                                     │
│          back_populates="rooms"                                           │
│      )                                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Database (PostgreSQL)                               │
│                                                                           │
│  ┌──────────────┐                                                        │
│  │  countries   │                                                        │
│  ├──────────────┤                                                        │
│  │ id (PK)      │                                                        │
│  │ name (UNIQUE)│                                                        │
│  │ iso_code     │                                                        │
│  └──────────────┘                                                        │
│       │                                                                   │
│       │ 1:N (CASCADE)                                                     │
│       ▼                                                                   │
│  ┌──────────────┐                                                        │
│  │   cities     │                                                        │
│  ├──────────────┤                                                        │
│  │ id (PK)      │                                                        │
│  │ name         │                                                        │
│  │ country_id   │◄─── FK                                                  │
│  └──────────────┘                                                        │
│       │                                                                   │
│       │ 1:N (CASCADE)                                                     │
│       ▼                                                                   │
│  ┌──────────────┐         ┌──────────────────┐                          │
│  │   hotels     │         │  hotels_images    │                          │
│  ├──────────────┤         ├──────────────────┤                          │
│  │ id (PK)      │◄────────│ hotel_id (FK, PK) │                          │
│  │ title (UNIQ) │         │ image_id (FK, PK) │                          │
│  │ city_id (FK) │         └──────────────────┘                          │
│  │ address      │                  │                                    │
│  │ postal_code  │                  │                                    │
│  │ check_in_time│                  │                                    │
│  │ check_out_...│                  │                                    │
│  └──────────────┘                  │                                    │
│       │                             │                                    │
│       │ 1:N                         │                                    │
│       ▼                             │                                    │
│  ┌──────────────┐                   │                                    │
│  │   rooms      │                   │                                    │
│  ├──────────────┤                   │                                    │
│  │ id (PK)      │                   │                                    │
│  │ hotel_id (FK)│                   │                                    │
│  │ title        │                   │                                    │
│  │ description  │                   │                                    │
│  │ price        │                   │                                    │
│  │ quantity     │                   │                                    │
│  └──────────────┘                   │                                    │
│       │                             │                                    │
│       │ 1:N                         │                                    │
│       │                             │                                    │
│       │                             │                                    │
│       │                             ▼                                    │
│       │                    ┌──────────────┐                              │
│       │                    │   images     │                              │
│       │                    ├──────────────┤                              │
│       │                    │ id (PK)      │                              │
│       │                    │ filename     │                              │
│       │                    │ original_... │                              │
│       │                    │ width        │                              │
│       │                    │ height       │                              │
│       │                    └──────────────┘                              │
│       │                                                                   │
│       │ N:M (CASCADE)                                                     │
│       ▼                                                                   │
│  ┌──────────────────┐                                                    │
│  │ rooms_facilities  │                                                    │
│  ├──────────────────┤                                                    │
│  │ room_id (FK, PK)  │                                                    │
│  │ facility_id (FK)  │                                                    │
│  └──────────────────┘                                                    │
│       │                                                                   │
│       │                                                                   │
│       ▼                                                                   │
│  ┌──────────────┐                                                        │
│  │  facilities  │                                                        │
│  ├──────────────┤                                                        │
│  │ id (PK)      │                                                        │
│  │ title        │                                                        │
│  └──────────────┘                                                        │
│                                                                           │
│  ┌──────────────┐                                                        │
│  │   users      │                                                        │
│  ├──────────────┤                                                        │
│  │ id (PK)      │                                                        │
│  │ email (UNIQ) │                                                        │
│  │ hashed_pass  │                                                        │
│  │ first_name   │                                                        │
│  │ last_name    │                                                        │
│  │ telegram_id  │                                                        │
│  │ pachca_id    │                                                        │
│  └──────────────┘                                                        │
│       │                                                                   │
│       │ 1:N                                                               │
│       ▼                                                                   │
│  ┌──────────────┐                                                        │
│  │  bookings    │                                                        │
│  ├──────────────┤                                                        │
│  │ id (PK)      │                                                        │
│  │ room_id (FK) │                                                        │
│  │ user_id (FK) │                                                        │
│  │ date_from    │                                                        │
│  │ date_to      │                                                        │
│  │ price        │                                                        │
│  │ created_at   │                                                        │
│  └──────────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Детальная схема для разных операций

### 1. GET запрос (чтение данных)

```
HTTP GET /hotels/1/rooms/5
    │
    ▼
[API Endpoint] get_room_by_id()
    │
    ▼
[Repository] get_by_id(5)
    │
    ▼
[SQL Query] SELECT * FROM rooms WHERE id = 5
    │
    ▼
[Database] Возвращает данные
    │
    ▼
[ORM] RoomsOrm(id=5, title="...", ...)
    │
    ▼
[Data Mapper] _to_schema(orm_obj)
    │
    ▼
[Pydantic Schema] SchemaRoom(id=5, title="...", ...)
    │
    ▼
[API Response] JSON {"id": 5, "title": "...", ...}
```

### 2. POST запрос (создание данных)

```
HTTP POST /hotels/1/rooms
Body: {"title": "Комната", "price": 2000, "facility_ids": [1, 2]}
    │
    ▼
[API Endpoint] create_room()
    │
    ▼
[Pydantic Validation] Room(title="...", price=2000, facility_ids=[1,2])
    │
    ▼
[Repository] create(title="...", price=2000, hotel_id=1)
    │
    ▼
[ORM] instance = RoomsOrm(title="...", price=2000, hotel_id=1)
    │
    ▼
[Database] INSERT INTO rooms (title, price, hotel_id) VALUES (...)
    │
    ▼
[Repository] update_room_facilities(room_id, [1, 2])
    │
    ▼
[Database] INSERT INTO rooms_facilities (room_id, facility_id) VALUES ...
    │
    ▼
[Data Mapper] _to_schema(instance)
    │
    ▼
[API Response] {"status": "OK"}
```

### 3. PUT запрос (обновление данных)

```
HTTP PUT /hotels/1/rooms/5
Body: {"title": "Новое название", "facility_ids": [2, 3]}
    │
    ▼
[API Endpoint] update_room()
    │
    ▼
[Pydantic Validation] Room(title="...", facility_ids=[2,3])
    │
    ▼
[Repository] edit(id=5, title="...")
    │
    ▼
[ORM] setattr(instance, "title", "...")
    │
    ▼
[Database] UPDATE rooms SET title = '...' WHERE id = 5
    │
    ▼
[Repository] update_room_facilities(5, [2, 3])
    │
    ▼
[Database] DELETE FROM rooms_facilities WHERE room_id=5 AND facility_id=1
    │         INSERT INTO rooms_facilities (room_id, facility_id) VALUES (5, 3)
    │
    ▼
[Data Mapper] _to_schema(updated_instance)
    │
    ▼
[API Response] {"status": "OK"}
```

## Ключевые принципы архитектуры

### 1. Разделение слоев (Layered Architecture)

```
┌─────────────────────────────────────────┐
│  Presentation Layer (API)               │  ← FastAPI endpoints
│  - Валидация HTTP запросов              │
│  - Обработка ошибок                     │
│  - Возврат JSON ответов                 │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Application Layer (Schemas)            │  ← Pydantic models
│  - Валидация входных данных             │
│  - Структура ответов                    │
│  - Бизнес-логика валидации              │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Domain Layer (Repositories)            │  ← Data Mapper
│  - Преобразование ORM → Schema          │
│  - Бизнес-логика работы с данными       │
│  - Абстракция доступа к данным          │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Data Access Layer (ORM Models)          │  ← SQLAlchemy
│  - Маппинг таблиц БД на классы          │
│  - SQL запросы                          │
│  - Управление связями                   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Database Layer (PostgreSQL)            │  ← База данных
│  - Хранение данных                      │
│  - Транзакции                           │
│  - Индексы и ограничения                │
└─────────────────────────────────────────┘
```

### 2. Data Mapper Pattern

```
┌─────────────────────────────────────────────────────────────┐
│  ORM Object (RoomsOrm)                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ id: 5                                                │   │
│  │ title: "Стандартный номер"                          │   │
│  │ price: 2000                                         │   │
│  │ facilities: [FacilitiesOrm(id=1), FacilitiesOrm(..)]│   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ _to_schema()
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Pydantic Schema (SchemaRoom)                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ id: 5                                                │   │
│  │ title: "Стандартный номер"                          │   │
│  │ price: 2000                                         │   │
│  │ facilities: [SchemaFacility(id=1, title="Wi-Fi"), ..]│   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ JSON serialization
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  HTTP Response (JSON)                                        │
│  {                                                           │
│    "id": 5,                                                  │
│    "title": "Стандартный номер",                             │
│    "price": 2000,                                            │
│    "facilities": [                                           │
│      {"id": 1, "title": "Wi-Fi"}                            │
│    ]                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

### 3. Преимущества Data Mapper

✅ **Разделение ответственности**
   - API слой не знает об ORM объектах
   - Репозитории управляют преобразованием
   - Схемы независимы от структуры БД

✅ **Гибкость**
   - Можно изменить структуру БД без изменения API
   - Можно изменить структуру ответа без изменения БД
   - Легко добавлять вычисляемые поля

✅ **Тестируемость**
   - Можно мокировать репозитории
   - Схемы можно тестировать отдельно
   - ORM модели изолированы

## Примеры преобразований

### Простое преобразование (FacilitiesRepository)

```python
# ORM → Schema (простое, структура совпадает)
ORM:  FacilitiesOrm(id=1, title="Wi-Fi")
      ↓ SchemaFacility.model_validate(orm_obj)
Schema: SchemaFacility(id=1, title="Wi-Fi")
```

### Сложное преобразование (HotelsRepository)

```python
# ORM → Schema (сложное, нужно извлечь вложенные данные)
ORM:  HotelsOrm(
        id=1,
        title="Отель",
        city=CitiesOrm(name="Москва", country=CountriesOrm(name="Россия"))
      )
      ↓ _to_schema() - извлекает city.name и country.name
Schema: SchemaHotel(
          id=1,
          title="Отель",
          city="Москва",        # строка, не объект
          country="Россия"      # строка, не объект
        )
```

### Преобразование с relationships (RoomsRepository)

```python
# ORM → Schema (с many-to-many связью)
ORM:  RoomsOrm(
        id=5,
        title="Комната",
        facilities=[
          FacilitiesOrm(id=1, title="Wi-Fi"),
          FacilitiesOrm(id=2, title="Кондиционер")
        ]
      )
      ↓ _to_schema() - преобразует список ORM в список Schema
Schema: SchemaRoom(
          id=5,
          title="Комната",
          facilities=[
            SchemaFacility(id=1, title="Wi-Fi"),
            SchemaFacility(id=2, title="Кондиционер")
          ]
        )
```

## Зависимости между слоями

```
API Layer (api/)
    │
    ├─→ Использует: Schemas (schemas/)
    │   └─→ Room, SchemaRoom, MessageResponse
    │
    ├─→ Использует: Repositories (repositories/)
    │   └─→ RoomsRepository, HotelsRepository
    │
    └─→ Использует: Dependencies (api/dependencies.py)
        └─→ DBDep, PaginationDep

Repository Layer (repositories/)
    │
    ├─→ Использует: ORM Models (models/)
    │   └─→ RoomsOrm, HotelsOrm, FacilitiesOrm
    │
    ├─→ Использует: Schemas (schemas/)
    │   └─→ SchemaRoom, SchemaFacility (для возврата)
    │
    └─→ Использует: Utils (repositories/utils.py)
        └─→ apply_pagination, apply_text_filter

ORM Models (models/)
    │
    └─→ Использует: SQLAlchemy Base
        └─→ Определяет структуру таблиц БД

Schemas (schemas/)
    │
    └─→ Использует: Pydantic BaseModel
        └─→ Валидация и сериализация данных
```

## Поток данных: Request → Response

```
1. HTTP Request
   POST /hotels/1/rooms
   Body: {"title": "Комната", "price": 2000, "facility_ids": [1, 2]}

2. FastAPI Router
   → Валидирует параметры пути (hotel_id=1)
   → Парсит JSON body

3. Pydantic Schema Validation
   → Room(title="Комната", price=2000, facility_ids=[1, 2])
   → Валидирует типы и ограничения

4. API Endpoint Logic
   → Проверяет существование отеля (get_or_404)
   → Извлекает facility_ids
   → Создает room_data

5. Repository.create()
   → Создает ORM объект: RoomsOrm(title="...", price=2000)
   → Добавляет в сессию
   → Выполняет INSERT в БД

6. Repository.update_room_facilities()
   → Валидирует существование facilities
   → Выполняет INSERT в rooms_facilities

7. Data Mapper._to_schema()
   → Преобразует RoomsOrm → SchemaRoom
   → Загружает facilities через selectinload
   → Преобразует FacilitiesOrm → SchemaFacility

8. API Response
   → Возвращает MessageResponse(status="OK")
   → FastAPI сериализует в JSON

9. HTTP Response
   200 OK
   {"status": "OK"}
```

## Ключевые моменты

🔑 **API слой никогда не работает с ORM объектами напрямую**
   - Всегда через репозитории
   - Всегда получает Pydantic схемы

🔑 **Репозитории - единственное место преобразования ORM → Schema**
   - Метод `_to_schema()` в каждом репозитории
   - Явное преобразование, не через `from_attributes=True`

🔑 **Схемы независимы от ORM**
   - Могут иметь другую структуру
   - Могут содержать вычисляемые поля
   - Могут объединять данные из нескольких таблиц

🔑 **ORM модели отражают структуру БД**
   - Прямое соответствие таблицам
   - Relationships для связей
   - Типы данных соответствуют колонкам БД

## Middleware и обработка исключений

### HTTP Logging Middleware

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HTTPLoggingMiddleware                                 │
│                                                                           │
│  Логирует все HTTP запросы в формате:                                    │
│  client_host - "method path?query protocol" status_code                 │
│                                                                           │
│  Пример:                                                                  │
│  127.0.0.1 - "GET /hotels/1/rooms?page=1 HTTP/1.1" 200                  │
│                                                                           │
│  Особенности:                                                             │
│  - Работает только для основного приложения (не для тестов)              │
│  - Логирует в root logger                                               │
│  - Измеряет время обработки запроса (для будущих метрик)                │
└─────────────────────────────────────────────────────────────────────────┘
```

**Реализация:** `src/middleware/http_logging.py`

### Глобальные обработчики исключений

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Exception Handling Layer                              │
│                                                                           │
│  1. database_exception_handler (DatabaseError)                           │
│     ├─ IntegrityError → 409 CONFLICT                                     │
│     ├─ OperationalError → 503 SERVICE_UNAVAILABLE                      │
│     └─ Другие DatabaseError → 500 INTERNAL_SERVER_ERROR                  │
│                                                                           │
│  2. general_exception_handler (Exception)                                │
│     └─ Все необработанные исключения → 500 INTERNAL_SERVER_ERROR         │
│                                                                           │
│  Все исключения логируются с полным traceback через logger.error()        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Реализация:** `src/middleware/exception_handler.py`

**Регистрация в main.py:**
```python
app.add_exception_handler(DatabaseError, database_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
```

## Система логирования

### Архитектура логирования

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Logging System                                         │
│                                                                           │
│  setup_logging()                                                          │
│    ├─ RotatingFileHandler (logs/app.log)                                 │
│    │  - Максимум 10 МБ на файл                                            │
│    │  - 5 резервных копий                                                 │
│    │  - Кодировка UTF-8                                                   │
│    │                                                                       │
│    └─ StreamHandler (stdout)                                             │
│       - Вывод в консоль                                                   │
│                                                                           │
│  Формат: [YYYY-MM-DD HH:MM:SS] [LEVEL] [name] message                    │
│                                                                           │
│  Настройка уровней:                                                       │
│  - uvicorn, fastapi, celery, alembic → пропагируют в root logger          │
│  - sqlalchemy.engine → только WARNING и выше, не пропагирует             │
└─────────────────────────────────────────────────────────────────────────┘
```

**Реализация:** `src/utils/logger.py`

**Использование:**
```python
from src.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Сообщение")
logger.error("Ошибка", exc_info=True)
```

## Lifespan события (Startup/Shutdown)

### Startup Handler

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    startup_handler()                                     │
│                                                                           │
│  1. Настройка тестовой БД (если DB_NAME == "test")                       │
│  2. Применение миграций Alembic                                          │
│  3. Проверка подключения к PostgreSQL                                   │
│  4. Проверка подключения к Redis                                         │
│  5. Инициализация FastAPI Cache (Redis backend)                          │
│  6. Очистка старых временных файлов (> 1 часа)                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Shutdown Handler

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    shutdown_handler()                                    │
│                                                                           │
│  1. Закрытие соединений с PostgreSQL (SQLAlchemy engine)                 │
│  2. Закрытие соединений с Redis                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Реализация:** `src/utils/startup.py`

## Кэширование (Redis)

### Архитектура кэширования

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Cache (Redis Backend)                         │
│                                                                           │
│  Используется для кэширования:                                           │
│  - Списки отелей (TTL: 300 секунд)                                       │
│  - Детали отелей (TTL: 300 секунд)                                       │
│  - Списки номеров (TTL: 300 секунд)                                       │
│  - Детали номеров (TTL: 300 секунд)                                       │
│                                                                           │
│  Декоратор: @cache(expire=300, namespace="hotels")                      │
│                                                                           │
│  Инвалидация кэша:                                                       │
│  - При создании/изменении/удалении отелей → invalidate_cache("hotels")   │
│  - При создании/изменении/удалении номеров → invalidate_cache("rooms")  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Реализация:**
- Инициализация: `src/utils/startup.py` (startup_handler)
- Использование: `@cache` декоратор из `fastapi_cache.decorator`
- Инвалидация: `src/utils/api_helpers.py` → `invalidate_cache()`

## Аутентификация и авторизация (JWT)

### Архитектура аутентификации

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    JWT Authentication Flow                               │
│                                                                           │
│  1. Регистрация (POST /auth/register)                                    │
│     ├─ Валидация email (уникальность)                                   │
│     ├─ Хеширование пароля (bcrypt)                                       │
│     └─ Создание пользователя в БД                                        │
│                                                                           │
│  2. Вход (POST /auth/login)                                              │
│     ├─ Проверка email и пароля                                           │
│     ├─ Создание JWT токена                                               │
│     └─ Установка токена в HTTP-only cookie                                │
│                                                                           │
│  3. Защищенные эндпоинты                                                 │
│     ├─ Извлечение токена из cookie или Authorization header              │
│     ├─ Валидация и декодирование JWT                                     │
│     ├─ Получение пользователя из БД                                      │
│     └─ Инъекция current_user в эндпоинт                                  │
│                                                                           │
│  4. Выход (POST /auth/logout)                                            │
│     └─ Удаление токена из cookie                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Реализация:**
- Сервис: `src/services/auth.py` (AuthService)
- API: `src/api/auth.py`
- Dependency: `src/api/dependencies.py` → `get_current_user()`

**Особенности:**
- Пароли хешируются с помощью bcrypt (автоматическое обрезание до 72 байт)
- JWT токены содержат `sub` (user_id) и `email`
- Токены устанавливаются в HTTP-only cookie для защиты от XSS
- Поддержка `secure` cookie (только HTTPS) через настройки
- SameSite=lax для защиты от CSRF

## Фоновые задачи (Celery)

### Архитектура Celery

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Celery Task Processing                                │
│                                                                           │
│  Задачи:                                                                  │
│  - process_image: Обработка изображений отелей                          │
│    ├─ Валидация размера (минимум 1000px по ширине)                      │
│    ├─ Создание ресайзов: 200px, 500px, 1000px                           │
│    ├─ Сохранение в static/images/                                        │
│    └─ Создание записей в БД (ImagesOrm)                                  │
│                                                                           │
│  Брокер/Backend: Redis                                                    │
│                                                                           │
│  Особенности:                                                             │
│  - Синхронное ожидание результата (timeout=30 сек)                       │
│  - Обработка ошибок с удалением временных файлов                         │
│  - Поддержка разных БД (booking/test) через db_name                     │
└─────────────────────────────────────────────────────────────────────────┘
```

**Реализация:**
- Celery app: `src/tasks/celery_app.py`
- Задачи: `src/tasks/tasks.py`
- Использование: `src/api/images.py` → `process_image.delay()`

## Структура проекта (актуальная на 3.2.2026)

```
fastapi/src/
├── api/                          # API Layer (FastAPI роутеры)
│   ├── auth.py                   # Аутентификация (register, login, logout)
│   ├── bookings.py               # Бронирования
│   ├── cities.py                 # Города
│   ├── countries.py              # Страны
│   ├── dependencies.py           # FastAPI dependencies (DBDep, CurrentUserDep, etc.)
│   ├── facilities.py            # Удобства
│   ├── hotels.py                 # Отели
│   ├── images.py                 # Изображения отелей
│   ├── rooms.py                  # Номера
│   └── users.py                  # Пользователи
│
├── middleware/                   # Middleware
│   ├── exception_handler.py      # Глобальные обработчики исключений
│   └── http_logging.py           # Логирование HTTP запросов
│
├── models/                       # ORM Models (SQLAlchemy)
│   ├── bookings.py
│   ├── cities.py
│   ├── countries.py
│   ├── facilities.py
│   ├── hotels.py
│   ├── images.py
│   ├── rooms.py
│   └── users.py
│
├── repositories/                 # Repository Layer (Data Mapper)
│   ├── base.py                   # Базовый репозиторий
│   ├── bookings.py
│   ├── cities.py
│   ├── countries.py
│   ├── facilities.py
│   ├── hotels.py
│   ├── images.py
│   ├── rooms.py
│   ├── users.py
│   ├── utils.py                  # Утилиты (пагинация, фильтрация)
│   └── mappers/                   # Data Mappers
│       ├── base.py
│       ├── bookings_mapper.py
│       ├── cities_mapper.py
│       ├── countries_mapper.py
│       ├── facilities_mapper.py
│       ├── hotels_mapper.py
│       ├── rooms_mapper.py
│       └── users_mapper.py
│
├── schemas/                      # Pydantic Schemas
│   ├── bookings.py
│   ├── cities.py
│   ├── common.py                 # MessageResponse, общие схемы
│   ├── countries.py
│   ├── facilities.py
│   ├── hotels.py
│   ├── images.py
│   ├── rooms.py
│   └── users.py
│
├── services/                     # Business Logic Services
│   └── auth.py                   # AuthService (JWT, bcrypt)
│
├── tasks/                        # Celery задачи
│   ├── celery_app.py             # Конфигурация Celery
│   └── tasks.py                  # Фоновые задачи
│
├── utils/                        # Утилиты
│   ├── api_helpers.py           # Хелперы для API (get_or_404, handle_validation_error)
│   ├── db_manager.py             # Менеджер БД сессий и транзакций
│   ├── logger.py                 # Настройка логирования
│   ├── migrations.py             # Утилиты для миграций
│   └── startup.py                 # Startup/shutdown handlers
│
├── connectors/                   # Коннекторы
│   └── redis_connector.py        # Менеджер Redis соединений
│
├── config.py                     # Настройки приложения (Pydantic Settings)
├── db.py                         # SQLAlchemy engine и session makers
├── base.py                       # SQLAlchemy Base
└── main.py                       # Точка входа FastAPI приложения
```

## Технологический стек

- **Web Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 (async)
- **Database:** PostgreSQL
- **Cache:** Redis (FastAPI Cache)
- **Task Queue:** Celery (Redis broker/backend)
- **Authentication:** JWT (PyJWT)
- **Password Hashing:** bcrypt
- **Validation:** Pydantic
- **Migrations:** Alembic
- **Logging:** Python logging (RotatingFileHandler)
- **Type Checking:** Pyright
- **Linting/Formatting:** Ruff

## Поток запроса с учетом всех компонентов

```
1. HTTP Request
   GET /hotels/1/rooms/5
   Headers: Cookie: access_token=...

2. HTTPLoggingMiddleware
   → Логирует запрос
   → Измеряет время обработки

3. FastAPI Router
   → Парсит путь и параметры
   → Извлекает JWT токен из cookie/header

4. Authentication (если требуется)
   → Валидация JWT токена
   → Получение пользователя из БД
   → Инъекция current_user в эндпоинт

5. API Endpoint
   → Валидация параметров
   → Проверка кэша (если есть @cache)
   → Вызов репозитория

6. Repository Layer
   → SQL запрос к БД
   → Преобразование ORM → Schema (Data Mapper)
   → Возврат Schema

7. Response
   → Сериализация Schema в JSON
   → Установка в кэш (если есть @cache)
   → HTTP Response

8. Exception Handling (если ошибка)
   → database_exception_handler или general_exception_handler
   → Логирование ошибки
   → JSON Response с ошибкой

9. HTTPLoggingMiddleware
   → Логирует ответ (status_code)
   → Возврат response клиенту
```

