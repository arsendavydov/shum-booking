# Shum Booking - бэкенд сервиса бронирования отелей на FastAPI

Развернут в K3s‑кластере, использует PostgreSQL, Redis, Celery, Nginx. Полноценный CI/CD через GitHub Actions или GitLab.

**🌐 Production:** https://async-black.ru/apps/shum-booking/docs

## Цели проекта

- **Продакшен-ready архитектура** - асинхронность, слоистая структура, разделение ответственности, CI/CD
- **Безопасность** - JWT-аутентификация с refresh токенами, rate limiting, HTTPS, защита от основных уязвимостей
- **Наблюдаемость** - Prometheus-метрики, структурированное логирование, health checks
- **Устойчивость** - graceful shutdown, retry-логика, проверка готовности компонентов, автоматическое восстановление

---

## Стек технологий

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic
- **База данных**: PostgreSQL 16
- **Кэш / rate limiting / сессии**: Redis 7 (alpine)
- **Очереди и фоновые задачи**: Celery
- **Веб‑сервер / reverse proxy**: Nginx
- **Контейнеры**: Docker, Docker Compose
- **Оркестрация**: K3s
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
  - Фоновые задачи (обработка изображений)
  - Работает в отдельном деплойменте, общается с тем же PostgreSQL/Redis

- **Nginx**
  - Reverse proxy перед FastAPI
  - Работает за Kubernetes Ingress
  - Поддерживает `/apps/shum-booking` как префикс (`ROOT_PATH`)
  - Реализует rate limiting на уровне Nginx 

- **Kubernetes (K3s)**
  - Namespace `booking`
  - Отдельные deployment/statefulset для fastapi, celery, nginx, postgres, redis
  - PVC для:
    - `postgres-data-postgres-0` (20Gi)
    - `redis-data-pvc` (5Gi)
    - `booking-images-pvc` (5Gi)

- **SSL / Ingress**
  - Ingress `booking-ingress` с аннотацией `cert-manager.io/cluster-issuer: "letsencrypt-prod"`
  - Cert‑manager автоматически получает и продлевает сертификат для `async-black.ru`
  - Включён HTTPS и принудительный redirect с HTTP → HTTPS

Детальная схема потока данных и слоёв описана в `ARCHITECTURE.md`.

---

## Окружения и конфигурация

Все чувствительные данные и настройки выносятся в `.env`‑файлы:

- `.local.env` - локальная разработка
- `.test.env` - тесты
- `.prod.env` - продакшен 

Для каждого окружения есть **шаблон**, который коммитится в репозиторий:

- `.local.env.template` → скопировать в `.local.env`
- `.test.env.template` → скопировать в `.test.env`
- `.prod.env.template` → скопировать в `.prod.env` (на сервере)


В продакшене `.prod.env` хранится **на сервере**, а CI/CD подхватывает оттуда значения и формирует ConfigMap/Secret.

---

## Локальный запуск

Требования:
- Docker + Docker Compose


### 1. Подготовить `.local.env`

Создай файл `.local.env` на основе шаблона:

```bash
cp .local.env.template .local.env
```

Минимально нужны:
- `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME`
- `JWT_SECRET_KEY`
- `RATE_LIMIT_*`

### 2. Поднять локальный стек через Docker Compose

Из корня проекта:

```bash
docker-compose -f docker-compose.local.yml up --build
```

Что поднимется:
- PostgreSQL на `localhost:5432`
- Redis на `localhost:6379`
- FastAPI приложение 
- Nginx (reverse proxy) - по умолчанию можно открыть в браузере:
  - Swagger: `http://localhost:8000/docs` 



## Тестирование

Проект использует многоуровневое тестирование:

- **Unit‑тесты** (`tests/unit_tests`) - изолированные тесты сервисов, репозиториев, утилит с моками
- **API‑тесты** (`tests/api_tests`) - интеграционные тесты эндпоинтов FastAPI, проверка валидации и бизнес-логики
- **E2E тесты** (`tests/e2e_tests`) - end-to-end тесты полных пользовательских сценариев (регистрация → бронирование → отмена)
- **Тесты health/metrics** (`tests/api_tests/test_health.py`, `tests/metrics`) - проверка health checks и Prometheus метрик
- **Нагрузочные тесты** (`tests/load_tests`) - тестирование производительности через Locust

Запуск основных проверок (из директории `fastapi`):

```bash
./scripts/lint.sh   # ruff + pyright
pytest              # все тесты
```

---

## Продакшен и деплой

Продакшен развёрнут на K3s‑сервере и управляется через **GitHub Actions**:

- `.github/workflows/deploy.yml`:
  - сборка Docker‑образов `fastapi` и `nginx`
  - пуш образов в GitHub Container Registry (ghcr.io)
  - запуск тестов перед деплоем (Ruff, Pyright, Pytest (unit_tests))
  - деплой в K3s:
    - SSH‑подключение к серверу
    - получение `kubeconfig`
    - создание/обновление ConfigMap и Secret на основе `.prod.env` на сервере
    - применение манифестов из `k3s/*.yaml`
    - проверка готовности всех компонентов после деплоя

Манифесты Kubernetes:
- `k3s/namespace.yaml` - namespace `booking`
- `k3s/storageclass.yaml` - storage
- `k3s/postgres-statefulset.yaml` - PostgreSQL
- `k3s/redis-deployment.yaml` - Redis
- `k3s/fastapi-deployment.yaml`, `fastapi-service.yaml`
- `k3s/celery-deployment.yaml`
- `k3s/nginx-deployment.yaml`, `nginx-service.yaml`, `nginx-configmap.yaml`
- `k3s/pvc.yaml` - PVC для изображений
- `k3s/cert-manager-issuer.yaml` - ClusterIssuer’ы Let’s Encrypt
- `k3s/ingress.yaml` - Ingress с TLS и префиксом `/apps/shum-booking`

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

---

## Метрики и наблюдаемость

FastAPI приложение экспонирует Prometheus‑совместимые метрики:

- эндпоинт: `/metrics` (за Nginx/Ingress)
- метрики:
  - стандартные Python/Prometheus (GC, CPU, память, файлы)
  - бизнес‑метрики:
    - `auth_registrations_total`
    - `auth_logins_total{status="success|failure"}` и др.

Для ручной проверки достаточно открыть `/metrics` в продакшене (за Nginx/Ingress).

В кластере также есть:
- `metrics-server` - для `kubectl top`
- health‑checks и readiness‑пробы для всех подов

---

## Безопасность

Ключевые моменты:

- Все чувствительные данные - в `.env`.
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


## Документация

- **`README.md`** (этот файл) - обзор проекта и быстрый старт
- **`ARCHITECTURE.md`** - детальная архитектура и поток данных
- **`CHANGELOG.md`** - история изменений и релизов
- **`fastapi/README.md`** - документация FastAPI приложения
- **`ci/README.md`** - документация по CI/CD процессу
- **`ci/github/README.md`** - описание GitHub Actions workflow



