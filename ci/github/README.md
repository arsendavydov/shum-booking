## GitHub Actions (деплой, общий с GitLab логикой)

В будущем сюда будут перенесены конфигурации GitHub Actions:

- workflow’ы для:
  - линтинга и типизации (ruff, pyright);
  - unit‑ и API‑тестов;
  - сборки Docker‑образов;
  - деплоя в тот же K3s‑кластер (по аналогии с GitLab CI/CD).

Реальные файлы GitHub Actions лежат в `.github/workflows/`.  
Основная логика деплоя и работы с кластером K3s общая для GitLab и GitHub и вынесена в:

- `ci/common/check-active-provider.sh` — проверка `ACTIVE_CI_PROVIDER` в `~/.prod.env` на сервере;
- `ci/gitlab/get-kubeconfig.sh` — получение kubeconfig с сервера по SSH;
- `ci/gitlab/create-configmap-and-secret.sh` — загрузка `.prod.env` с сервера, создание ConfigMap и Secret;
- `ci/gitlab/apply-manifests.sh` — применение всех Kubernetes‑манифестов с ретраями.

GitLab CI (`.gitlab-ci.yml`) и GitHub Actions (`.github/workflows/deploy.yml`) выступают как тонкие обёртки,  
которые подготавливают окружение (SSH ключ, переменные CI) и вызывают эти общие скрипты.


