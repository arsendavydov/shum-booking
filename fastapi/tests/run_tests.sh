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

# Запускаем тестовый контейнер FastAPI (использует .test.env с DB_NAME=test)
echo "🚀 Запуск тестового контейнера FastAPI..."
COMPOSE_BAKE=true docker-compose -f docker-compose.test.yml up -d

# Ждем готовности FastAPI (миграции применятся автоматически при старте, если DB_NAME=test)
echo "⏳ Ожидание готовности FastAPI и применения миграций..."
sleep 30

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
python3.11 -m pytest tests/api_tests/ -v --color=yes --tb=short 2>&1 | tee -a "$LOG_FILE"
TEST_EXIT_CODE=${PIPESTATUS[0]}

# Возвращаемся в корень проекта
cd "$PROJECT_ROOT"

# Удаляем тестовый контейнер (всегда, даже при ошибках)
echo "🧹 Удаление тестового контейнера..."
docker-compose -f docker-compose.test.yml down || true

echo "✅ Очистка завершена"

# Возвращаем код выхода тестов
exit $TEST_EXIT_CODE

