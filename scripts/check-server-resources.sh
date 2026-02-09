#!/bin/bash
# Скрипт для проверки ресурсов сервера через kubectl

set -e

echo "🔍 Проверка ресурсов сервера..."
echo ""

# Проверка ресурсов ноды
echo "📊 Ресурсы ноды:"
kubectl describe node | grep -A 10 "Allocated resources:" || kubectl top node || true
echo ""

# Детальная информация о ноде
echo "📋 Детальная информация о ноде:"
kubectl get node -o json | jq -r '.items[0] | {
  name: .metadata.name,
  cpu_capacity: .status.capacity.cpu,
  memory_capacity: .status.capacity.memory,
  cpu_allocatable: .status.allocatable.cpu,
  memory_allocatable: .status.allocatable.memory,
  cpu_requests: (.status.allocatedResources.requests.cpu // "N/A"),
  memory_requests: (.status.allocatedResources.requests.memory // "N/A")
}' 2>/dev/null || kubectl describe node | grep -E "(Capacity|Allocatable|Requests)" | head -20
echo ""

# Текущее использование ресурсов подами
echo "📊 Текущее использование ресурсов подами:"
kubectl top pods -A 2>/dev/null || echo "⚠️  metrics-server не установлен или недоступен"
echo ""

# Список всех подов с их resource requests/limits
echo "📋 Ресурсы подов:"
kubectl get pods -A -o json | jq -r '.items[] | {
  namespace: .metadata.namespace,
  name: .metadata.name,
  cpu_request: (.spec.containers[0].resources.requests.cpu // "N/A"),
  memory_request: (.spec.containers[0].resources.requests.memory // "N/A"),
  cpu_limit: (.spec.containers[0].resources.limits.cpu // "N/A"),
  memory_limit: (.spec.containers[0].resources.limits.memory // "N/A")
}' 2>/dev/null || echo "⚠️  jq не установлен, используем kubectl describe"
echo ""

# Альтернативный способ без jq
echo "📋 Сводка ресурсов подов (без jq):"
for ns in $(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}'); do
  echo "Namespace: $ns"
  kubectl get pods -n $ns -o custom-columns=NAME:.metadata.name,CPU-REQ:.spec.containers[*].resources.requests.cpu,MEM-REQ:.spec.containers[*].resources.requests.memory,CPU-LIM:.spec.containers[*].resources.limits.cpu,MEM-LIM:.spec.containers[*].resources.limits.memory 2>/dev/null | head -10
  echo ""
done

