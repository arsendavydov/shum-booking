## GitHub Actions (основной CI/CD для деплоя)

GitHub Actions используется как **основной способ деплоя** в продакшн.

### Workflow файлы

Основной workflow находится в `.github/workflows/deploy.yml` и включает:

- **Линтинг и проверка типов**:
  - Ruff для проверки кода
  - Pyright для проверки типов
- **Тестирование**:
  - Unit-тесты (Pytest)
- **Сборка и деплой**:
  - Сборка Docker‑образов `fastapi` и `nginx`
  - Пуш образов в GitHub Container Registry (ghcr.io)
  - Деплой в K3s кластер:
    - SSH‑подключение к серверу
    - Получение `kubeconfig`
    - Создание/обновление ConfigMap и Secret на основе `.prod.env` на сервере
    - Применение манифестов из `k3s/*.yaml`
    - Проверка готовности всех компонентов после деплоя

### Общие скрипты

Основная логика деплоя и работы с кластером K3s вынесена в общие скрипты:

- `ci/common/check-active-provider.sh` — проверка `ACTIVE_CI_PROVIDER` в `~/.prod.env` на сервере
- `ci/gitlab/get-kubeconfig.sh` — получение kubeconfig с сервера по SSH (используется и GitHub Actions)
- `ci/gitlab/create-configmap-and-secret.sh` — загрузка `.prod.env` с сервера, создание ConfigMap и Secret
- `ci/gitlab/apply-manifests.sh` — применение всех Kubernetes‑манифестов с ретраями

GitHub Actions (`.github/workflows/deploy.yml`) подготавливает окружение (SSH ключ, переменные CI из GitHub Secrets) и вызывает эти общие скрипты.


