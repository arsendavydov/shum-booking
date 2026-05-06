## CI папка

Эта папка предназначена для всего, что относится к CI/CD:

- конфигурации пайплайнов (GitHub Actions и др.)
- вспомогательные скрипты для деплоя и проверки
- документация по процессу доставки кода

Текущая структура:

- `ci/` - общие скрипты для деплоя (используются и GitHub Actions, и GitLab CI)
  - `get-kubeconfig.sh` - получение kubeconfig с сервера по SSH
  - `create-configmap-and-secret.sh` - загрузка `.prod.env` с сервера, создание ConfigMap и Secret
  - `apply-manifests.sh` - применение всех Kubernetes-манифестов с ретраями
  - `helpers.sh` - вспомогательные функции (SSH, kubectl, retry логика)
- `ci/common/` - общие скрипты для проверки активного CI провайдера
  - `check-active-provider.sh` - проверка `ACTIVE_CI_PROVIDER` в `~/.prod.env` на сервере
- `ci/github/` - документация и специфичные скрипты для GitHub Actions
- `ci/gitlab/` - документация и специфичные скрипты для GitLab CI

### Основной CI/CD

**GitHub Actions** используется как основной способ деплоя в продакшн:
- Workflow файлы находятся в `.github/workflows/deploy.yml`
- Все переменные и секреты хранятся в GitHub Secrets
- Деплой выполняется автоматически при пуше в `main` ветку
- Использует общие скрипты из `ci/`

**GitLab CI** также поддерживается:
- Конфигурация в `.gitlab-ci.yml`
- Использует те же общие скрипты из `ci/`

### Общие скрипты

Основная логика деплоя и работы с кластером K3s вынесена в общие скрипты в корне `ci/`:
- **`ci/get-kubeconfig.sh`**: получение kubeconfig с сервера по SSH (используется и GitHub Actions, и GitLab CI)
- **`ci/create-configmap-and-secret.sh`**: загрузка `.prod.env` с сервера, создание ConfigMap и Secret
- **`ci/apply-manifests.sh`**: применение всех Kubernetes-манифестов с ретраями
- **`ci/helpers.sh`**: вспомогательные функции для работы с SSH, kubectl и retry логики

GitHub Actions (`.github/workflows/deploy.yml`) и GitLab CI (`.gitlab-ci.yml`) подготавливают окружение (SSH ключ, переменные CI из Secrets) и вызывают эти общие скрипты.


