from unittest.mock import patch, MagicMock


class TestClient:
    def test_v1_health_check(self, client):
        response = client.get("/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_v1_version_with_registry(self, client):
        """Test /v1/version when a model registry exists."""
        # Mock the registry to return version info
        mock_version_info = MagicMock()
        mock_version_info.version = "v1.2.3"
        mock_version_info.run_id = "20260201_120000"
        mock_version_info.timestamp = 1706788800.0

        with patch("app.api.v1.router.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.get_current_version.return_value = mock_version_info
            mock_get_registry.return_value = mock_registry

            response = client.get("/v1/version")
            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "1.2.3"  # 'v' prefix stripped
            assert data["run_id"] == "20260201_120000"
            assert data["timestamp"] == 1706788800.0

    def test_v1_version_without_registry(self, client):
        """Test /v1/version when no model registry exists (fallback)."""
        with patch("app.api.v1.router.get_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_registry.get_current_version.return_value = None
            mock_get_registry.return_value = mock_registry

            response = client.get("/v1/version")
            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "0.1.0"
            assert data["run_id"] == "unknown"
