#!/bin/bash
# Скрипт для генерации base64-encoded KUBECONFIG для GitLab CI/CD

set -e

echo "🔐 Генерация base64-encoded KUBECONFIG для GitLab CI/CD"
echo ""

# Проверяем наличие kubeconfig
KUBECONFIG_FILE="${KUBECONFIG:-$HOME/.kube/config}"

if [ ! -f "$KUBECONFIG_FILE" ]; then
    echo "❌ Файл kubeconfig не найден: $KUBECONFIG_FILE"
    echo ""
    echo "Укажите путь к kubeconfig файлу:"
    read -p "Путь к kubeconfig: " KUBECONFIG_FILE
    
    if [ ! -f "$KUBECONFIG_FILE" ]; then
        echo "❌ Файл не найден: $KUBECONFIG_FILE"
        exit 1
    fi
fi

echo "📋 Используется файл: $KUBECONFIG_FILE"
echo ""

# Проверяем содержимое
echo "🔍 Проверка содержимого kubeconfig..."
if ! kubectl config view --kubeconfig="$KUBECONFIG_FILE" >/dev/null 2>&1; then
    echo "⚠️  Предупреждение: kubeconfig может быть невалидным"
    read -p "Продолжить? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        exit 1
    fi
fi

# Показываем информацию о кластере
echo ""
echo "📊 Информация о кластере:"
kubectl config view --kubeconfig="$KUBECONFIG_FILE" --minify --raw 2>/dev/null | grep -E "server:|name:" | head -5 || echo "Не удалось получить информацию"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Base64-encoded KUBECONFIG:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Генерируем base64
if command -v base64 >/dev/null 2>&1; then
    BASE64_CONFIG=$(cat "$KUBECONFIG_FILE" | base64 -w 0 2>/dev/null || cat "$KUBECONFIG_FILE" | base64)
else
    echo "❌ Команда base64 не найдена"
    exit 1
fi

echo "$BASE64_CONFIG"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Копируем в буфер обмена (если доступно)
if command -v pbcopy >/dev/null 2>&1; then
    echo "$BASE64_CONFIG" | pbcopy
    echo "✅ Скопировано в буфер обмена!"
elif command -v xclip >/dev/null 2>&1; then
    echo "$BASE64_CONFIG" | xclip -selection clipboard
    echo "✅ Скопировано в буфер обмена!"
else
    echo "ℹ️  Скопируйте значение выше вручную"
fi

echo ""
echo "📝 Инструкция по добавлению в GitLab:"
echo ""
echo "1. Откройте: https://gitlab.com/arsen-davydov-main/shum_booking_v2/-/settings/ci_cd"
echo "2. Раскройте секцию 'Variables'"
echo "3. Нажмите 'Add variable'"
echo "4. Заполните:"
echo "   - Key: KUBECONFIG"
echo "   - Value: (вставьте значение выше)"
echo "   - Type: Variable"
echo "   - Flags: ✅ Protected, ✅ Masked"
echo "5. Нажмите 'Add variable'"
echo ""
echo "⚠️  ВАЖНО:"
echo "   - Убедитесь, что токены/сертификаты в kubeconfig не истекут"
echo "   - Проверьте права доступа к кластеру"
echo "   - Для продакшена используйте отдельный ServiceAccount с минимальными правами"
echo ""

# Сохраняем в файл (опционально)
read -p "Сохранить в файл? (y/n): " SAVE_FILE
if [ "$SAVE_FILE" = "y" ] || [ "$SAVE_FILE" = "Y" ]; then
    OUTPUT_FILE="kubeconfig-base64.txt"
    echo "$BASE64_CONFIG" > "$OUTPUT_FILE"
    echo "✅ Сохранено в: $OUTPUT_FILE"
    echo "⚠️  НЕ КОММИТЬТЕ этот файл в Git!"
fi

