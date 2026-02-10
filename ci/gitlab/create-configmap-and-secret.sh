#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"

: "${KUBE_NAMESPACE:?KUBE_NAMESPACE is required}"

echo "📋 Создание ConfigMap и Secret из .prod.env на сервере..."

TMP_ENV="/tmp/prod.env"
TMP_ENV_CLEAN="/tmp/prod.env.clean"

echo "📥 Загрузка переменных из .prod.env на сервере..."
if ssh -i "$K3S_SSH_KEY_PATH" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o BatchMode=yes \
    "$K3S_SSH_HOST" "test -f ~/.prod.env && cat ~/.prod.env" > "$TMP_ENV" 2>/dev/null; then
  echo "✅ Файл .prod.env найден на сервере, загружаем переменные..."
  grep -v '^#' "$TMP_ENV" | grep -v '^$' | grep '=' > "$TMP_ENV_CLEAN" 2>/dev/null || true
  if [[ -f "$TMP_ENV_CLEAN" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$TMP_ENV_CLEAN" 2>/dev/null || true
    set +a
    rm -f "$TMP_ENV" "$TMP_ENV_CLEAN"
    echo "✅ Переменные загружены из .prod.env на сервере"
  else
    echo "⚠️  Не удалось обработать .prod.env файл"
    rm -f "$TMP_ENV" "$TMP_ENV_CLEAN"
  fi
else
  echo "⚠️  Файл .prod.env не найден на сервере или не удалось его прочитать"
  echo "   Используем переменные из GitLab CI/CD Variables (если заданы)"
fi

echo "🔐 Проверка статуса GitLab/GitHub токенов (из .prod.env)..."

print_token_status() {
  local name="$1"
  local token="$2"
  local expected_prefix="$3"
  local exp_day="$4"

  if [[ -z "$token" ]]; then
    echo "⚠️  $name токен не задан"
    return 0
  fi

  if [[ "$token" == "$expected_prefix"* ]]; then
    echo "✅ $name токен задан и формат выглядит корректным (префикс $expected_prefix)"
  else
    echo "⚠️  $name токен задан, но имеет неожиданный формат (нет префикса $expected_prefix)"
  fi

  if [[ -n "$exp_day" ]]; then
    echo "   Дата истечения $name токена: $exp_day"
  else
    echo "   Дата истечения $name токена не указана"
  fi
}

print_token_status "GitLab" "${GITLAB_PERSONAL_ACCESS_TOKEN:-}" "glpat-" "${GITLAB_TOKEN_EXPIRATION_DAY:-}"
print_token_status "GitHub" "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" "github_pat_" "${GITHUB_TOKEN_EXPIRATION_DAY:-}"

if [[ -z "${RATE_LIMIT_PER_MINUTE:-}" || -z "${RATE_LIMIT_AUTH_PER_MINUTE:-}" ]]; then
  echo "❌ ОШИБКА: Переменные RATE_LIMIT_PER_MINUTE и RATE_LIMIT_AUTH_PER_MINUTE должны быть заданы!"
  echo "   Либо в GitLab CI/CD Variables, либо в файле ~/.prod.env на сервере"
  exit 1
fi

echo "✅ Переменные rate limit найдены:"
echo "   RATE_LIMIT_PER_MINUTE=${RATE_LIMIT_PER_MINUTE}"
echo "   RATE_LIMIT_AUTH_PER_MINUTE=${RATE_LIMIT_AUTH_PER_MINUTE}"

ensure_tunnel

kubectl delete configmap booking-config -n "$KUBE_NAMESPACE" --ignore-not-found=true --request-timeout=30s || true

kubectl create configmap booking-config \
  --from-literal=DB_HOST="${DB_HOST:-postgres-service}" \
  --from-literal=DB_PORT="${DB_PORT:-5432}" \
  --from-literal=DB_NAME="${DB_NAME:-booking}" \
  --from-literal=REDIS_HOST="${REDIS_HOST:-redis-service}" \
  --from-literal=REDIS_PORT="${REDIS_PORT:-6379}" \
  --from-literal=REDIS_DB="${REDIS_DB:-0}" \
  --from-literal=JWT_ALGORITHM="${JWT_ALGORITHM:-HS256}" \
  --from-literal=JWT_ACCESS_TOKEN_EXPIRE_MINUTES="${JWT_ACCESS_TOKEN_EXPIRE_MINUTES:-30}" \
  --from-literal=JWT_REFRESH_TOKEN_EXPIRE_DAYS="${JWT_REFRESH_TOKEN_EXPIRE_DAYS:-30}" \
  --from-literal=JWT_COOKIE_SECURE="${JWT_COOKIE_SECURE:-true}" \
  --from-literal=LOG_LEVEL="${LOG_LEVEL:-INFO}" \
  --from-literal=LOG_FORMAT_JSON="${LOG_FORMAT_JSON:-true}" \
  --from-literal=MAX_IMAGE_FILE_SIZE_MB="${MAX_IMAGE_FILE_SIZE_MB:-10}" \
  --from-literal=RATE_LIMIT_ENABLED="${RATE_LIMIT_ENABLED:-true}" \
  --from-literal=RATE_LIMIT_PER_MINUTE="${RATE_LIMIT_PER_MINUTE}" \
  --from-literal=RATE_LIMIT_AUTH_PER_MINUTE="${RATE_LIMIT_AUTH_PER_MINUTE}" \
  --from-literal=PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}" \
  --from-literal=PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}" \
  --from-literal=ROOT_PATH="${ROOT_PATH:-/apps/shum-booking}" \
  --namespace="$KUBE_NAMESPACE" \
  --request-timeout=30s || {
    echo "⚠️  Не удалось создать ConfigMap, возможно он уже существует"
  }

echo "✅ ConfigMap booking-config создан/обновлен"

echo "🔐 Создание Secret booking-secrets..."

TMP_ENV="/tmp/prod.env"
TMP_ENV_CLEAN="/tmp/prod.env.clean"

echo "📥 Загрузка переменных из .prod.env на сервере для Secret..."
if ssh -i "$K3S_SSH_KEY_PATH" \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o BatchMode=yes \
    "$K3S_SSH_HOST" "test -f ~/.prod.env && cat ~/.prod.env" > "$TMP_ENV" 2>/dev/null; then
  echo "✅ Файл .prod.env найден на сервере, загружаем переменные..."
  grep -v '^#' "$TMP_ENV" | grep -v '^$' | grep '=' > "$TMP_ENV_CLEAN" 2>/dev/null || true
  if [[ -f "$TMP_ENV_CLEAN" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$TMP_ENV_CLEAN" 2>/dev/null || true
    set +a
    rm -f "$TMP_ENV" "$TMP_ENV_CLEAN"
    echo "✅ Переменные загружены из .prod.env на сервере"
  else
    echo "⚠️  Не удалось обработать .prod.env файл"
    rm -f "$TMP_ENV" "$TMP_ENV_CLEAN"
  fi
else
  echo "⚠️  Файл .prod.env не найден на сервере или не удалось его прочитать"
  echo "   Используем переменные из GitLab CI/CD Variables (если заданы)"
fi

if [[ -z "${DB_PASSWORD:-}" || -z "${JWT_SECRET_KEY:-}" ]]; then
  echo "❌ ОШИБКА: DB_PASSWORD или JWT_SECRET_KEY должны быть заданы!"
  echo "   Либо в GitLab CI/CD Variables, либо в файле ~/.prod.env на сервере"
  if ! kubectl get secret booking-secrets -n "$KUBE_NAMESPACE" &>/dev/null; then
    echo "❌ Secret booking-secrets не существует и не может быть создан без переменных!"
    exit 1
  fi
  echo "✅ Secret booking-secrets существует, используем существующий"
  exit 0
fi

kubectl delete secret booking-secrets -n "$KUBE_NAMESPACE" --ignore-not-found=true --request-timeout=30s || true

kubectl create secret generic booking-secrets \
  --from-literal=DB_USERNAME="${DB_USERNAME:-postgres}" \
  --from-literal=DB_PASSWORD="$DB_PASSWORD" \
  --from-literal=JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  --from-literal=REDIS_PASSWORD="${REDIS_PASSWORD:-}" \
  --namespace="$KUBE_NAMESPACE" \
  --request-timeout=30s || {
    echo "⚠️  Не удалось создать Secret, возможно он уже существует"
  }

echo "✅ Secret booking-secrets создан/обновлен"


