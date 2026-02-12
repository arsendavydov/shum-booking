#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

: "${KUBE_NAMESPACE:?KUBE_NAMESPACE is required}"

echo "🔧 Применение Kubernetes манифестов..."

ensure_tunnel

# Namespace и storageclass
apply_with_retry k3s/namespace.yaml
apply_with_retry k3s/storageclass.yaml

# PVC для изображений (с проверкой accessMode)
if kubectl get pvc booking-images-pvc -n "$KUBE_NAMESPACE" --request-timeout=30s &>/dev/null; then
  PVC_ACCESS_MODE=$(kubectl get pvc booking-images-pvc -n "$KUBE_NAMESPACE" -o jsonpath='{.spec.accessModes[0]}' 2>/dev/null || echo "")
  if [[ "$PVC_ACCESS_MODE" != "ReadWriteOnce" ]]; then
    echo "⚠️  PVC booking-images-pvc имеет неправильный accessMode: $PVC_ACCESS_MODE"
    echo "   Удаляем поды, использующие PVC..."
    kubectl delete deployment fastapi-app celery-worker nginx -n "$KUBE_NAMESPACE" --ignore-not-found=true || true
    sleep 3
    echo "   Удаляем старый PVC..."
    kubectl delete pvc booking-images-pvc -n "$KUBE_NAMESPACE" --ignore-not-found=true || true
    sleep 2
    echo "   Создаем новый PVC с правильными параметрами..."
    apply_with_retry k3s/pvc.yaml
    echo "   Ждем создания PVC..."
    sleep 3
  else
    echo "✅ PVC booking-images-pvc уже имеет правильный accessMode: ReadWriteOnce"
  fi
else
  echo "📦 PVC booking-images-pvc не существует, создаем..."
  apply_with_retry k3s/pvc.yaml
  sleep 2
fi

kubectl get pvc -n "$KUBE_NAMESPACE" || true

# База данных и кэш
echo "🔄 Обновление Postgres StatefulSet..."
# Удаляем существующий StatefulSet, чтобы избежать проблем с типами при patch'е
kubectl delete statefulset postgres -n "$KUBE_NAMESPACE" --ignore-not-found=true || true
sleep 3
apply_with_retry k3s/postgres-statefulset.yaml

echo "🔄 Обновление Redis Deployment и PVC..."
# Удаляем старый Deployment и PVC Redis, чтобы убрать старые last-applied с плейсхолдерами
kubectl delete deployment redis -n "$KUBE_NAMESPACE" --ignore-not-found=true || true
kubectl delete pvc redis-data-pvc -n "$KUBE_NAMESPACE" --ignore-not-found=true || true
sleep 3
apply_with_retry k3s/redis-deployment.yaml

echo "🔄 Применение ConfigMap для Nginx..."
apply_with_retry k3s/nginx-configmap.yaml

echo "🔄 Применение deployment'ов с обновленными ресурсами..."
kubectl delete deployment fastapi-app celery-worker nginx -n "$KUBE_NAMESPACE" --ignore-not-found=true || true
sleep 3
apply_with_retry k3s/fastapi-deployment.yaml
apply_with_retry k3s/fastapi-service.yaml
apply_with_retry k3s/celery-deployment.yaml
apply_with_retry k3s/nginx-deployment.yaml
apply_with_retry k3s/nginx-service.yaml

echo "🔐 Применение cert-manager ClusterIssuer..."
apply_with_retry k3s/cert-manager-issuer.yaml || echo "⚠️  cert-manager может быть не установлен, пропускаем"
apply_with_retry k3s/ingress.yaml

echo "📊 Статус подов после деплоя:"
kubectl get pods -n "$KUBE_NAMESPACE"
echo "✅ Деплой завершен! Поды запускаются в фоне."


