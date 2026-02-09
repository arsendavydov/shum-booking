#!/bin/bash
# Скрипт для создания пользователей на сервере для K3s и приложения

set -e

SERVER_IP="188.120.244.162"
ROOT_PASSWORD="XdeUuwHf_7ENZRH"

# Генерация паролей
K3S_ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-16)
APP_USER_PASSWORD=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-16)

echo "🔐 Создание пользователей на сервере..."
echo ""

# Создание скрипта для выполнения на сервере
cat > /tmp/setup_users.sh << 'REMOTE_SCRIPT'
#!/bin/bash
set -e

# Пароли передаются как аргументы
K3S_ADMIN_PASSWORD=$1
APP_USER_PASSWORD=$2

echo "📋 Создание пользователей..."

# Создать пользователя для K3s (k3s-admin)
if id "k3s-admin" &>/dev/null; then
    echo "⚠️  Пользователь k3s-admin уже существует"
else
    useradd -m -s /bin/bash k3s-admin
    echo "✅ Пользователь k3s-admin создан"
fi

# Установить пароль для k3s-admin
echo "k3s-admin:${K3S_ADMIN_PASSWORD}" | chpasswd

# Добавить k3s-admin в sudo группу
usermod -aG sudo k3s-admin
echo "✅ k3s-admin добавлен в группу sudo"

# Создать пользователя для приложения (app-user)
if id "app-user" &>/dev/null; then
    echo "⚠️  Пользователь app-user уже существует"
else
    useradd -m -s /bin/bash app-user
    echo "✅ Пользователь app-user создан"
fi

# Установить пароль для app-user
echo "app-user:${APP_USER_PASSWORD}" | chpasswd

# Создать директории для приложения
mkdir -p /home/app-user/app
mkdir -p /home/app-user/.kube
chown -R app-user:app-user /home/app-user/app
chown -R app-user:app-user /home/app-user/.kube

echo "✅ Директории для приложения созданы"

# Настроить SSH доступ (опционально - разрешить парольную аутентификацию)
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication no/#PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl reload sshd 2>/dev/null || service ssh reload 2>/dev/null || true

echo "✅ SSH настроен"

# Вывести информацию о пользователях
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Пользователи созданы:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "k3s-admin / ${K3S_ADMIN_PASSWORD}"
echo "app-user / ${APP_USER_PASSWORD}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
REMOTE_SCRIPT

# Копировать скрипт на сервер и выполнить
if command -v sshpass >/dev/null 2>&1; then
    sshpass -p "$ROOT_PASSWORD" scp -o StrictHostKeyChecking=no /tmp/setup_users.sh root@${SERVER_IP}:/tmp/setup_users.sh
    sshpass -p "$ROOT_PASSWORD" ssh -o StrictHostKeyChecking=no root@${SERVER_IP} "chmod +x /tmp/setup_users.sh && /tmp/setup_users.sh '${K3S_ADMIN_PASSWORD}' '${APP_USER_PASSWORD}'"
else
    echo "⚠️  sshpass не установлен. Выполните вручную:"
    echo ""
    echo "scp /tmp/setup_users.sh root@${SERVER_IP}:/tmp/"
    echo "ssh root@${SERVER_IP} 'chmod +x /tmp/setup_users.sh && /tmp/setup_users.sh \"${K3S_ADMIN_PASSWORD}\" \"${APP_USER_PASSWORD}\"'"
    echo ""
    echo "Или введите пароль root вручную при подключении"
fi

# Очистка
rm -f /tmp/setup_users.sh

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 УЧЕТНЫЕ ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "k3s-admin / ${K3S_ADMIN_PASSWORD}"
echo "app-user / ${APP_USER_PASSWORD}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Использование:"
echo "   k3s-admin - для установки и управления K3s (имеет sudo права)"
echo "   app-user - для запуска приложения (обычный пользователь)"
echo ""

