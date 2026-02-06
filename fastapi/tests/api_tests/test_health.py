import pytest


class TestHealthCheck:
    """Тесты для расширенных health checks"""

    def test_health_check_success(self, client):
        """Проверка успешного health check со всеми сервисами"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "database" in data
        assert "redis" in data
        assert "celery" in data
        assert "disk" in data

        assert data["status"] in ["ok", "degraded"]
        assert data["database"] == "connected"
        assert data["redis"] == "connected"

        # Celery может быть "ok", "no_workers" или "error"
        assert data["celery"]["status"] in ["ok", "no_workers", "error"]

        # Disk должен быть "ok" или "warning"
        assert data["disk"]["status"] in ["ok", "warning", "error"]
        assert "free_percent" in data["disk"]
        assert "free_gb" in data["disk"]

    def test_health_check_database_info(self, client):
        """Проверка наличия информации о БД в health check"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["database"] == "connected"

    def test_health_check_redis_info(self, client):
        """Проверка наличия информации о Redis в health check"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["redis"] == "connected"

    def test_health_check_celery_info(self, client):
        """Проверка наличия информации о Celery в health check"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "celery" in data
        assert "status" in data["celery"]

        # Если workers найдены, должны быть поля workers_count и workers
        if data["celery"]["status"] == "ok":
            assert "workers_count" in data["celery"]
            assert "workers" in data["celery"]
            assert isinstance(data["celery"]["workers"], list)
            assert data["celery"]["workers_count"] > 0

    def test_health_check_disk_info(self, client):
        """Проверка наличия информации о дисковом пространстве в health check"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "disk" in data
        assert "status" in data["disk"]
        assert "total_gb" in data["disk"]
        assert "used_gb" in data["disk"]
        assert "free_gb" in data["disk"]
        assert "free_percent" in data["disk"]
        assert "min_free_percent" in data["disk"]

        # Проверяем, что значения числовые и положительные
        assert isinstance(data["disk"]["total_gb"], (int, float))
        assert isinstance(data["disk"]["free_gb"], (int, float))
        assert isinstance(data["disk"]["free_percent"], (int, float))
        assert data["disk"]["total_gb"] > 0
        assert data["disk"]["free_gb"] >= 0
        assert 0 <= data["disk"]["free_percent"] <= 100

    def test_readiness_check(self, client):
        """Проверка readiness check"""
        response = client.get("/ready")
        assert response.status_code == 200

        data = response.json()
        assert "ready" in data
        assert "timestamp" in data
        assert data["ready"] is True

    def test_liveness_check(self, client):
        """Проверка liveness check"""
        response = client.get("/live")
        assert response.status_code == 200

        data = response.json()
        assert "alive" in data
        assert "timestamp" in data
        assert data["alive"] is True

