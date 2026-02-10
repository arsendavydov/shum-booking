#!/usr/bin/env bash 
set -euo pipefail

# Общие вспомогательные функции для GitLab CI деплоя в K3s

K3S_SSH_KEY_PATH="${K3S_SSH_KEY_PATH:-$HOME/.ssh/k3s_key}"
K3S_SSH_HOST="${K3S_SSH_USER}@${K3S_SERVER_IP}"
KUBE_CONFIG_PATH="${KUBE_CONFIG_PATH:-$HOME/.kube/config}"

log() {
  echo -e "$@"
}

ensure_ssh_key() {
  if [[ ! -f "$K3S_SSH_KEY_PATH" ]]; then
    log "❌ SSH ключ не найден по пути $K3S_SSH_KEY_PATH"
    exit 1
  fi
}

ensure_tunnel() {
  # Проверяем только порт (kubectl может быть медленным)
  if ! nc -z 127.0.0.1 6443 2>/dev/null; then
    log "⚠️  Туннель не работает, пересоздаем..."
    pkill -f "ssh.*6443:127.0.0.1:6443" || true
    sleep 2
    ssh -i "$K3S_SSH_KEY_PATH" \
      -o StrictHostKeyChecking=no \
      -o ServerAliveInterval=10 \
      -o ServerAliveCountMax=10 \
      -o ConnectTimeout=20 \
      -o TCPKeepAlive=yes \
      -o Compression=no \
      -o BatchMode=yes \
      -f -N -L 6443:127.0.0.1:6443 \
      "$K3S_SSH_HOST"
    sleep 3
    # Финальная проверка
    if ! nc -z 127.0.0.1 6443 2>/dev/null; then
      log "❌ Не удалось создать SSH‑туннель к K3s API"
      exit 1
    fi
    log "✅ SSH туннель к K3s API восстановлен"
  fi
}

check_api() {
  local max_attempts=3
  for i in $(seq 1 "$max_attempts"); do
    if kubectl get --raw=/healthz --request-timeout=10s &>/dev/null; then
      return 0
    fi
    log "   API не отвечает, попытка $i/$max_attempts..."
    sleep 2
  done
  log "⚠️  API медленно отвечает, но продолжаем..."
  return 0
}

apply_with_retry() {
  local file=$1
  local max_attempts=3
  for i in $(seq 1 "$max_attempts"); do
    log "🔄 Попытка $i/$max_attempts применения $file..."
    ensure_tunnel
    check_api || true
    if kubectl apply -f "$file" --request-timeout=120s 2>&1; then
      log "✅ $file успешно применен"
      return 0
    fi
    log "⏳ Попытка $i/$max_attempts не удалась, повторяем..."
    sleep 5
  done
  log "❌ Не удалось применить $file после $max_attempts попыток"
  return 1
}


