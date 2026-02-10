# Shum Booking — продакшен‑ready сервис бронирования на FastAPI

Shum Booking — проект сервиса бронирования отелей.  
Он развёрнут в продакшене на K3s‑кластере, использует PostgreSQL, Redis, Celery, Nginx и имеет полноценный CI/CD через GitHub Actions.

**🌐 Production:** https://async-black.ru/apps/shum-booking/docs

## Основные цели проекта

- Отработать **полный цикл**: от локальной разработки до деплоя в Kubernetes
- Обеспечить **безопасность, наблюдаемость и устойчивость** сервиса

---

## Стек технологий

- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async), Pydantic
- **База данных**: PostgreSQL 16
- **Кэш / rate limiting / сессии**: Redis 7 (alpine)
- **Очереди и фоновые задачи**: Celery
- **Веб‑сервер / reverse proxy**: Nginx
- **Контейнеры**: Docker, Docker Compose
- **Оркестрация**: K3s (Kubernetes)
- **CI/CD**: GitHub Actions (build + deploy в K3s)
- **SSL / HTTPS**: cert‑manager + Let’s Encrypt (авто‑обновление сертификатов)
- **Мониторинг**: Prometheus‑совместимые метрики (`/metrics`)

---

## Архитектура 

### Компоненты

- **FastAPI приложение**
  - Слоистая архитектура: API → Services → Repositories → Models (ORM) → PostgreSQL
  - JWT‑аутентификация (access + refresh токены)
  - CRUD для стран, городов, отелей, номеров, удобств, бронирований и пользователей
  - Rate limiting (ограничение запросов, в т.ч. на auth эндпоинты)
  - Метрики и health‑checks:
    - `/health`, `/ready`, `/live`
    - `/metrics` (Prometheus)

- **Celery worker**
  - Фоновые задачи (например, обработка изображений)
  - Работает в отдельном деплойменте, общается с тем же PostgreSQL/Redis

- **Nginx**
  - Reverse proxy перед FastAPI
  - Работает за Kubernetes Ingress
  - Поддерживает `/apps/shum-booking` как префикс (`ROOT_PATH`)
  - Реализует rate limiting на уровне Nginx (значения берутся из `.prod.env`)

- **Kubernetes (K3s)**
  - Namespace `booking`
  - Отдельные deployment/statefulset для fastapi, celery, nginx, postgres, redis
  - PVC для:
    - `postgres-data-postgres-0` (20Gi)
    - `redis-data-pvc` (5Gi)
    - `booking-images-pvc` (5Gi) — хранение изображений

- **SSL / Ingress**
  - Ingress `booking-ingress` с аннотацией `cert-manager.io/cluster-issuer: "letsencrypt-prod"`
  - Cert‑manager автоматически получает и продлевает сертификат для `async-black.ru`
  - Включён HTTPS и принудительный redirect с HTTP → HTTPS

Детальная схема потока данных и слоёв описана в `ARCHITECTURE.md`.

---

## Окружения и конфигурация

Все чувствительные данные и настройки выносятся в `.env`‑файлы:

- `.local.env` — локальная разработка
- `.test.env` — тесты
- `.prod.env` — продакшен 

Для каждого окружения есть **шаблон**, который коммитится в репозиторий:

- `.local.env.template` → скопировать в `.local.env`
- `.test.env.template` → скопировать в `.test.env`
- `.prod.env.template` → скопировать в `.prod.env` (на сервере)

Пример ключевых переменных (см. `.prod.env.template` / `.local.env.template`):

- База данных:
  - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`
- JWT:
  - `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- Redis:
  - `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
- Rate limiting:
  - `RATE_LIMIT_ENABLED`
  - `RATE_LIMIT_PER_MINUTE`
  - `RATE_LIMIT_AUTH_PER_MINUTE`
- Лимиты по загрузке изображений:
  - `MAX_IMAGE_FILE_SIZE_MB`
- Продакшен‑домен и путь:
  - `DOMAIN=async-black.ru`
  - `ROOT_PATH=/apps/shum-booking`
- SSL / Let’s Encrypt:
  - `LETSENCRYPT_EMAIL`
  - `LETSENCRYPT_SERVER=production|staging`
- Kubernetes деплой:
  - `FASTAPI_REPLICAS`, `CELERY_REPLICAS`, `NGINX_REPLICAS`, `POSTGRES_REPLICAS`, `REDIS_REPLICAS`
  - Ресурсы и лимиты для всех подов (`*_MEMORY_REQUEST`, `*_CPU_REQUEST`, `*_MEMORY_LIMIT`, `*_CPU_LIMIT`)

В продакшене `.prod.env` хранится **на сервере**, а CI/CD подхватывает оттуда значения и формирует ConfigMap/Secret.

---

## Локальный запуск

Требования:
- Docker + Docker Compose
- Python 3.11 (если хочешь запускать без контейнеров)

### 1. Подготовить `.local.env`

Создай файл `.local.env` на основе шаблона:

```bash
cp .local.env.template .local.env
```

Минимально нужны:
- `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME`
- `JWT_SECRET_KEY` (любой достаточно длинный hex/строка)
- `RATE_LIMIT_*` (можно временно поставить высокие значения при нагрузочном тестировании)

### 2. Поднять локальный стек через Docker Compose

Из корня проекта:

```bash
docker-compose -f docker-compose.local.yml up --build
```

Что поднимется:
- PostgreSQL на `localhost:5432`
- Redis на `localhost:6379`
- FastAPI приложение (доступно через Nginx или напрямую по порту, если настроено)
- Nginx (reverse proxy) — по умолчанию можно открыть в браузере:
  - Swagger: `http://localhost:8000/docs` (или порт из `docker-compose.local.yml`)

### 3. Применить миграции (если нужно)

В контейнере FastAPI:

```bash
docker exec -it fastapi_app bash
alembic upgrade head
```

---

## Тестирование

Тесты живут в `fastapi/tests` и делятся на:

- **Unit‑тесты** (`tests/unit_tests`) — сервисы, репозитории, утилиты
- **API‑тесты** (`tests/api_tests`) — проверка эндпоинтов FastAPI
- **Тесты health/metrics** (`tests/api_tests/test_health.py`, tests/metrics)
- **Нагрузочные / вспомогательные** (`tests/load_tests`, `user_tests/test_api.py`)

Запуск основных тестов (из директории `fastapi`):

```bash
cd fastapi
./scripts/lint.sh       # линтеры и типизация (ruff + pyright)
pytest                  # все тесты
pytest tests/api_tests  # только API‑тесты
```

Отдельный комплексный сценарий тестирования продакшн‑API есть в `user_tests/test_api.py`
(специально вынесен из репозитория и игнорируется `.gitignore`).

---

## Продакшен и деплой

Продакшен развёрнут на K3s‑сервере и управляется через **GitHub Actions**:

- `.github/workflows/deploy.yml`:
  - сборка Docker‑образов `fastapi` и `nginx`
  - пуш образов в GitHub Container Registry (ghcr.io)
  - запуск тестов перед деплоем (Ruff, Pyright, Pytest)
  - деплой в K3s:
    - SSH‑подключение к серверу
    - получение `kubeconfig`
    - создание/обновление ConfigMap и Secret на основе `.prod.env` на сервере
    - применение манифестов из `k3s/*.yaml`
    - проверка готовности всех компонентов после деплоя

Манифесты Kubernetes:
- `k3s/namespace.yaml` — namespace `booking`
- `k3s/storageclass.yaml` — storage
- `k3s/postgres-statefulset.yaml` — PostgreSQL
- `k3s/redis-deployment.yaml` — Redis
- `k3s/fastapi-deployment.yaml`, `fastapi-service.yaml`
- `k3s/celery-deployment.yaml`
- `k3s/nginx-deployment.yaml`, `nginx-service.yaml`, `nginx-configmap.yaml`
- `k3s/pvc.yaml` — PVC для изображений
- `k3s/cert-manager-issuer.yaml` — ClusterIssuer’ы Let’s Encrypt
- `k3s/ingress.yaml` — Ingress с TLS и префиксом `/apps/shum-booking`

---

## SSL / HTTPS и автопродление сертификата

За SSL отвечает **cert-manager** + **Let’s Encrypt**:

1. В кластере работает cert-manager (`cert-manager`, `cainjector`, `webhook` в namespace `cert-manager`).
2. Применён `ClusterIssuer letsencrypt-prod` (и `letsencrypt-staging`) из `k3s/cert-manager-issuer.yaml`.
3. `Ingress` (`k3s/ingress.yaml`) имеет:
   - аннотацию `cert-manager.io/cluster-issuer: "letsencrypt-prod"`
   - секцию `tls` с `secretName: booking-tls`.
4. Cert‑manager создаёт объект `Certificate`, получает сертификат у Let’s Encrypt и кладёт его в Secret `booking-tls`.
5. Далее cert-manager:
   - отслеживает срок действия сертификата;
   - за ~30 дней до истечения заново проходит ACME‑челлендж;
   - обновляет Secret с новым сертификатом;
   - Nginx Ingress автоматически подхватывает обновлённый сертификат без даунтайма.

Проверить статус можно командами:

```bash
sudo kubectl get pods -n cert-manager
sudo kubectl get certificate -n booking
sudo kubectl describe certificate booking-tls -n booking
```

---

## Метрики и наблюдаемость

FastAPI приложение экспонирует Prometheus‑совместимые метрики:

- эндпоинт: `/metrics` (за Nginx/Ingress)
- метрики:
  - стандартные Python/Prometheus (GC, CPU, память, файлы)
  - бизнес‑метрики:
    - `auth_registrations_total`
    - `auth_logins_total{status="success|failure"}` и др.

Примеры:

```bash
curl -s https://async-black.ru/apps/shum-booking/metrics | head -50
```

В кластере также есть:
- `metrics-server` — для `kubectl top`
- health‑checks и readiness‑пробы для всех подов

---

## Безопасность

Ключевые моменты:

- Все чувствительные данные — в `.env` (в Git не коммитятся).
- JWT‑аутентификация, refresh токены, отзыв токенов.
- Rate limiting:
  - отдельные лимиты для auth‑эндпоинтов и остальных.
- HTTPS везде (Let’s Encrypt + cert-manager).
- Firewall на сервере:
  - открыт только `22`, `80`, `443`.
- Логи:
  - структурированное логирование;
  - HTTP‑логи через middleware.

---

## Что ещё планируется улучшить

- Настроить полноценный мониторинг: Prometheus + Grafana, алерты
- Подключить HPA (Horizontal Pod Autoscaler) для FastAPI и Celery
- Расширить документацию с примерами запросов/ответов для API

---

## Документация

- **`README.md`** (этот файл) — обзор проекта и быстрый старт
- **`ARCHITECTURE.md`** — детальная архитектура и поток данных
- **`CHANGELOG.md`** — история изменений и релизов
- **`ci/README.md`** — документация по CI/CD процессу
- **`ci/github/README.md`** — описание GitHub Actions workflow



