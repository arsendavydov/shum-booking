#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

CONTAINER_NAME="fastapi_app"

if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Контейнер ${CONTAINER_NAME} не запущен!"
    echo "Запустите контейнеры: COMPOSE_BAKE=true docker compose -f docker-compose.local.yml up -d"
    exit 1
fi

ACTION="${1:-check}"

case "$ACTION" in
    check)
        echo "🔍 Запуск ruff check..."
        docker exec "${CONTAINER_NAME}" ruff check src/ tests/
        
        echo "🔍 Запуск pyright для проверки типов..."
        docker exec "${CONTAINER_NAME}" pyright src/
        
        echo "✅ Все проверки завершены!"
        ;;
    fix)
        echo "🔧 Запуск ruff check --fix --unsafe-fixes..."
        docker exec "${CONTAINER_NAME}" ruff check --fix --unsafe-fixes src/ tests/
        
        echo "✨ Запуск ruff format..."
        docker exec "${CONTAINER_NAME}" ruff format src/ tests/
        
        echo "✅ Линтинг и форматирование завершены!"
        ;;
    *)
        echo "Использование: $0 [check|fix]"
        echo ""
        echo "Команды:"
        echo "  check  - Проверить код (linting + type checking)"
        echo "  fix    - Исправить и отформатировать код"
        echo ""
        echo "По умолчанию выполняется 'check'"
        exit 1
        ;;
esac

