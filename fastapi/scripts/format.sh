#!/bin/bash

set -e

cd "$(dirname "$0")/.." || exit 1

echo "✨ Запуск ruff format..."
ruff format src/ tests/

echo "✅ Форматирование завершено!"

