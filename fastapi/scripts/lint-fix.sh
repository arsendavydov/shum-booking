#!/bin/bash

set -e

cd "$(dirname "$0")/.." || exit 1

echo "🔧 Запуск ruff check --fix..."
ruff check --fix src/ tests/

echo "✨ Запуск ruff format..."
ruff format src/ tests/

echo "✅ Линтинг и форматирование завершены!"

