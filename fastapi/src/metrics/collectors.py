"""
Модуль для сбора кастомных метрик Prometheus.

Содержит счетчики, гистограммы и другие метрики для мониторинга приложения.
"""

from prometheus_client import Counter, Gauge, Histogram

# ============================================================================
# Метрики аутентификации
# ============================================================================

auth_registrations_total = Counter(
    "auth_registrations_total",
    "Общее количество регистраций пользователей",
)

auth_logins_total = Counter(
    "auth_logins_total",
    "Общее количество попыток входа",
    ["status"],
)

auth_refresh_tokens_total = Counter(
    "auth_refresh_tokens_total",
    "Общее количество использований refresh токенов",
    ["status"],
)

auth_failed_attempts_total = Counter(
    "auth_failed_attempts_total",
    "Общее количество неудачных попыток аутентификации",
    ["reason"],
)

# ============================================================================
# Метрики базы данных
# ============================================================================

db_queries_total = Counter(
    "db_queries_total",
    "Общее количество запросов к базе данных",
    ["operation"],
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Время выполнения запросов к базе данных в секундах",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

db_connections_active = Gauge(
    "db_connections_active",
    "Количество активных соединений с базой данных",
)

db_connections_idle = Gauge(
    "db_connections_idle",
    "Количество неактивных соединений с базой данных",
)

# ============================================================================
# Метрики Redis/кэша
# ============================================================================

cache_operations_total = Counter(
    "cache_operations_total",
    "Общее количество операций с кэшем",
    ["operation", "namespace"],
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Общее количество попаданий в кэш",
    ["namespace"],
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Общее количество промахов кэша",
    ["namespace"],
)

cache_operation_duration_seconds = Histogram(
    "cache_operation_duration_seconds",
    "Время выполнения операций с кэшем в секундах",
    ["operation", "namespace"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

# ============================================================================
# Метрики rate limiting
# ============================================================================

rate_limit_requests_total = Counter(
    "rate_limit_requests_total",
    "Общее количество запросов, проверенных rate limiting",
    ["endpoint"],
)

rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Общее количество превышений лимита запросов",
    ["endpoint"],
)

# ============================================================================
# Метрики по эндпоинтам
# ============================================================================

api_requests_total = Counter(
    "api_requests_total",
    "Общее количество запросов к API",
    ["endpoint", "method", "status"],
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "Время обработки запросов к API в секундах",
    ["endpoint", "method"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

api_errors_total = Counter(
    "api_errors_total",
    "Общее количество ошибок API",
    ["endpoint", "error_type"],
)

# ============================================================================
# Системные метрики
# ============================================================================
# Примечание: process_resident_memory_bytes и process_cpu_seconds_total
# уже создаются автоматически prometheus-fastapi-instrumentator,
# поэтому мы их не дублируем здесь

app_uptime_seconds = Gauge(
    "app_uptime_seconds",
    "Время работы приложения в секундах",
)

app_info = Gauge(
    "app_info",
    "Информация о приложении",
    ["version"],
)

# ============================================================================
# Бизнес-метрики
# ============================================================================

bookings_created_total = Counter(
    "bookings_created_total",
    "Общее количество созданных бронирований",
)

hotels_created_total = Counter(
    "hotels_created_total",
    "Общее количество созданных отелей",
)

users_active_total = Gauge(
    "users_active_total",
    "Количество активных пользователей",
)

# Экспорт всех метрик для удобного импорта
__all__ = [
    "api_errors_total",
    "api_request_duration_seconds",
    "api_requests_total",
    "app_info",
    "app_uptime_seconds",
    "auth_failed_attempts_total",
    "auth_logins_total",
    "auth_refresh_tokens_total",
    "auth_registrations_total",
    "bookings_created_total",
    "cache_hits_total",
    "cache_misses_total",
    "cache_operation_duration_seconds",
    "cache_operations_total",
    "db_connections_active",
    "db_connections_idle",
    "db_queries_total",
    "db_query_duration_seconds",
    "hotels_created_total",
    "rate_limit_exceeded_total",
    "rate_limit_requests_total",
    "users_active_total",
]
