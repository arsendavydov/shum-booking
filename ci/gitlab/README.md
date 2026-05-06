## GitLab CI

Эта папка предназначена для документации и специфичных скриптов для GitLab CI/CD.

### Общие скрипты

Основная логика деплоя вынесена в общие скрипты в корне `ci/`:
- `ci/get-kubeconfig.sh` - получение kubeconfig с сервера
- `ci/create-configmap-and-secret.sh` - создание ConfigMap и Secret
- `ci/apply-manifests.sh` - применение Kubernetes манифестов
- `ci/helpers.sh` - вспомогательные функции

Эти скрипты используются как GitHub Actions, так и GitLab CI.

### Конфигурация

GitLab CI конфигурация находится в `.gitlab-ci.yml` в корне проекта.
