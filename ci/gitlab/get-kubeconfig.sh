#!/usr/bin/env bash
set -euo pipefail

# Получение kubeconfig с сервера через SSH

: "${K3S_SERVER_IP:?K3S_SERVER_IP is required}"
: "${K3S_SSH_USER:?K3S_SSH_USER is required}"

K3S_SSH_KEY_PATH="${K3S_SSH_KEY_PATH:-$HOME/.ssh/k3s_key}"
K3S_SSH_HOST="${K3S_SSH_USER}@${K3S_SERVER_IP}"
KUBE_CONFIG_PATH="${KUBE_CONFIG_PATH:-$HOME/.kube/config}"

mkdir -p "$(dirname "$K3S_SSH_KEY_PATH")"
mkdir -p "$(dirname "$KUBE_CONFIG_PATH")"

echo "📥 Получение kubeconfig с сервера..."

if ssh -i "$K3S_SSH_KEY_PATH" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o BatchMode=yes \
    "$K3S_SSH_HOST" "test -f ~/.kube/config && cat ~/.kube/config" > "$KUBE_CONFIG_PATH" 2>/dev/null; then
  echo "✅ Kubeconfig получен из ~/.kube/config"
elif ssh -i "$K3S_SSH_KEY_PATH" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o BatchMode=yes \
    "$K3S_SSH_HOST" "sudo cat /etc/rancher/k3s/k3s.yaml" > "$KUBE_CONFIG_PATH" 2>/dev/null; then
  echo "✅ Kubeconfig получен из /etc/rancher/k3s/k3s.yaml"
  sed -i "s|server: https://127.0.0.1:6443|server: https://$K3S_SERVER_IP:6443|g" "$KUBE_CONFIG_PATH"
else
  echo "❌ Не удалось получить kubeconfig с сервера!"
  exit 1
fi

chmod 600 "$KUBE_CONFIG_PATH"
export KUBECONFIG="$KUBE_CONFIG_PATH"


