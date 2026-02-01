#!/bin/bash

set -e

cd "$(dirname "$0")/.." || exit 1

echo "🔍 Запуск ruff check..."
ruff check src/ tests/

echo "🔍 Запуск pyright для проверки типов..."
pyright src/

echo "✅ Все проверки завершены!"

