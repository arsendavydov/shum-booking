#!/bin/bash
# Скрипт для генерации base64-encoded SSH ключа для доступа к K3s серверу

set -e

echo "🔐 Генерация base64-encoded SSH ключа для K3s сервера"
echo ""

# Проверяем наличие SSH ключа
SSH_KEY_FILE="${SSH_KEY_FILE:-$HOME/.ssh/id_rsa}"

if [ ! -f "$SSH_KEY_FILE" ]; then
    echo "❌ SSH ключ не найден: $SSH_KEY_FILE"
    echo ""
    echo "Укажите путь к SSH ключу для доступа к серверу K3s:"
    read -p "Путь к SSH ключу: " SSH_KEY_FILE
    
    if [ ! -f "$SSH_KEY_FILE" ]; then
        echo "❌ Файл не найден: $SSH_KEY_FILE"
        exit 1
    fi
fi

echo "📋 Используется файл: $SSH_KEY_FILE"
echo ""

# Проверяем, что это приватный ключ
if ! grep -q "BEGIN.*PRIVATE KEY" "$SSH_KEY_FILE"; then
    echo "⚠️  Предупреждение: файл не похож на приватный SSH ключ"
    read -p "Продолжить? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        exit 1
    fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Base64-encoded SSH Key:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Генерируем base64
if command -v base64 >/dev/null 2>&1; then
    BASE64_KEY=$(cat "$SSH_KEY_FILE" | base64 | tr -d '\n')
else
    echo "❌ Команда base64 не найдена"
    exit 1
fi

echo "$BASE64_KEY"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Копируем в буфер обмена (если доступно)
if command -v pbcopy >/dev/null 2>&1; then
    echo "$BASE64_KEY" | pbcopy
    echo "✅ Скопировано в буфер обмена!"
elif command -v xclip >/dev/null 2>&1; then
    echo "$BASE64_KEY" | xclip -selection clipboard
    echo "✅ Скопировано в буфер обмена!"
else
    echo "ℹ️  Скопируйте значение выше вручную"
fi

echo ""
echo "📝 Инструкция по добавлению в GitLab CI/CD Variables:"
echo ""
echo "1. Откройте: https://gitlab.com/arsen-davydov-main/shum_booking_v2/-/settings/ci_cd"
echo "2. Раскройте секцию 'Variables'"
echo "3. Нажмите 'Add variable'"
echo "4. Добавьте переменные:"
echo ""
echo "   Variable 1:"
echo "   - Key: K3S_SSH_KEY_BASE64"
echo "   - Value: (вставьте значение выше)"
echo "   - Type: Variable"
echo "   - Flags: ✅ Protected, ✅ Masked"
echo ""
echo "   Variable 2:"
echo "   - Key: K3S_SERVER_IP"
echo "   - Value: 188.120.244.162"
echo "   - Type: Variable"
echo "   - Flags: ✅ Protected"
echo ""
echo "   Variable 3:"
echo "   - Key: K3S_SSH_USER"
echo "   - Value: k3s-admin"
echo "   - Type: Variable"
echo "   - Flags: ✅ Protected"
echo ""
echo "5. Нажмите 'Add variable' для каждой"
echo ""
echo "⚠️  ВАЖНО:"
echo "   - Используйте приватный SSH ключ, который добавлен в ~/.ssh/authorized_keys на сервере"
echo "   - Ключ должен иметь доступ к пользователю k3s-admin на сервере 188.120.244.162"
echo ""

