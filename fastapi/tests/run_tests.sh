#!/bin/bash

# Скрипт для запуска тестов: запуск тестового контейнера -> проверка/применение миграций -> тесты -> удаление контейнера

echo "🚀 Запуск тестов..."

# Переходим в корень проекта (на два уровня выше от fastapi/tests/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Очистка предыдущего контейнера, если он остался
echo "🧹 Очистка предыдущих тестовых контейнеров..."
docker-compose -f docker-compose.test.yml down 2>/dev/null || true

# Запускаем тестовый контейнер FastAPI с автоматической пересборкой при необходимости
# Флаг --build пересоберет образ только если изменился Dockerfile или файлы в контексте (включая requirements.txt)
echo "🚀 Запуск тестового контейнера FastAPI (с автоматической проверкой и пересборкой образа при необходимости)..."
COMPOSE_BAKE=true docker-compose -f docker-compose.test.yml up -d --build

# Ждем немного, чтобы контейнер успел запуститься
sleep 5

# Проверяем логи на наличие ошибок импорта модулей (только если контейнер существует)
if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^fastapi_app_test$"; then
    echo "🔍 Проверка логов контейнера на ошибки..."
    if docker logs fastapi_app_test 2>&1 | grep -q "ModuleNotFoundError\|ImportError"; then
        echo "⚠️  Обнаружена ошибка импорта модуля. Пересобираем образ с --no-cache..."
        COMPOSE_BAKE=true docker-compose -f docker-compose.test.yml build --no-cache
        echo "🔄 Перезапускаем контейнер..."
        COMPOSE_BAKE=true docker-compose -f docker-compose.test.yml up -d
        sleep 5
    fi
fi

# Ждем готовности FastAPI (миграции применятся автоматически при старте, если DB_NAME=test)
echo "⏳ Ожидание готовности FastAPI и применения миграций..."
sleep 25

# Проверяем, что контейнер работает и отвечает
echo "🔍 Проверка доступности FastAPI..."
MAX_RETRIES=60
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8001/docs > /dev/null 2>&1; then
        echo "✅ FastAPI готов!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⏳ Ожидание... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 3
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ FastAPI не отвечает после $MAX_RETRIES попыток"
    docker logs fastapi_app_test --tail 50
    docker-compose -f docker-compose.test.yml down
    exit 1
fi

# Запускаем тесты (переходим в fastapi/ для запуска pytest)
echo "🧪 Запуск тестов..."
cd "$PROJECT_ROOT/fastapi"

# Запускаем тесты с записью результатов в файл через tee
LOG_FILE="$PROJECT_ROOT/fastapi/logs/app_test.log"

# Сначала запускаем unit тесты внутри контейнера (они не требуют БД или API)
echo "🧪 Запуск unit тестов..."
docker exec fastapi_app_test python -m pytest tests/unit_tests/ -v --color=yes --tb=short 2>&1 | tee -a "$LOG_FILE"
UNIT_TEST_EXIT_CODE=${PIPESTATUS[0]}

# Затем запускаем обычные тесты на хосте (они подключаются к API через localhost:8001)
echo "🧪 Запуск API тестов..."
python3.11 -m pytest tests/api_tests/ -v --color=yes --tb=short 2>&1 | tee -a "$LOG_FILE"
API_TEST_EXIT_CODE=${PIPESTATUS[0]}

# Затем запускаем тесты для индексов внутри контейнера (им нужен прямой доступ к БД)
echo "🧪 Запуск тестов для индексов БД..."
docker exec fastapi_app_test python -m pytest tests/database_tests/ -v --color=yes --tb=short 2>&1 | tee -a "$LOG_FILE"
INDEX_TEST_EXIT_CODE=${PIPESTATUS[0]}

# Если хотя бы один набор тестов упал, возвращаем ошибку
if [ $UNIT_TEST_EXIT_CODE -ne 0 ] || [ $API_TEST_EXIT_CODE -ne 0 ] || [ $INDEX_TEST_EXIT_CODE -ne 0 ]; then
    TEST_EXIT_CODE=1
else
    TEST_EXIT_CODE=0
fi

# Возвращаемся в корень проекта
cd "$PROJECT_ROOT"

# Удаляем тестовый контейнер (всегда, даже при ошибках)
echo "🧹 Удаление тестового контейнера..."
docker-compose -f docker-compose.test.yml down || true

echo "✅ Очистка завершена"

# Возвращаем код выхода тестов
exit $TEST_EXIT_CODE

