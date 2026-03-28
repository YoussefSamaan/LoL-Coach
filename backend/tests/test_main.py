import asyncio
import pytest
from unittest.mock import patch, MagicMock
from backend import main


class TestMain:
    def test_health_check_root(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "service": "lol-coach-backend"}

    def test_health_check_v1(self, client):
        r = client.get("/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_version(self, client):
        r = client.get("/version")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
        assert "run_id" in data
        # Should have either actual version info or fallback
        assert data["version"] is not None

    def test_version_fallback_no_registry(self, client):
        """Test /version endpoint when no model registry exists."""
        from unittest.mock import patch, MagicMock

        # Patch where ModelRegistry is imported (inside the version function)
        with patch("ml.registry.ModelRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_current_version.return_value = None
            mock_registry_class.return_value = mock_registry

            r = client.get("/version")
            assert r.status_code == 200
            data = r.json()
            assert data["version"] == "0.1.0"
            assert data["run_id"] == "unknown"

    def test_openapi_contains_v1_routes(self, client):
        """
        Ensures the v1 router is actually mounted.
        """
        r = client.get("/openapi.json")
        assert r.status_code == 200

        schema = r.json()
        assert "/health" in schema["paths"]
        assert "/v1/health" in schema["paths"]
        assert any(path.startswith("/v1/") for path in schema["paths"])

    def test_openapi_metadata(self, client):
        """
        Guards against accidental API metadata regressions.
        """
        r = client.get("/openapi.json")
        schema = r.json()

        assert schema["info"]["title"] == "LoL Coach Draft Assistant"
        assert schema["info"]["version"] == "0.1.0"

    def test_run_uses_default_env(self, monkeypatch):
        calls = {}

        def fake_run(app_str, host, port, reload):
            calls["app_str"] = app_str
            calls["host"] = host
            calls["port"] = port
            calls["reload"] = reload

        # Patch uvicorn.run that is imported inside main.run()
        monkeypatch.setattr("uvicorn.run", fake_run, raising=True)

        # Ensure env vars are not set
        monkeypatch.delenv("PORT", raising=False)
        monkeypatch.delenv("RELOAD", raising=False)

        main.run()

        assert calls == {
            "app_str": "backend.main:app",
            "host": "0.0.0.0",
            "port": 8000,
            "reload": True,
        }

    def test_run_reads_env_vars(self, monkeypatch):
        calls = {}

        def fake_run(app_str, host, port, reload):
            calls["app_str"] = app_str
            calls["host"] = host
            calls["port"] = port
            calls["reload"] = reload

        monkeypatch.setattr("uvicorn.run", fake_run, raising=True)

        monkeypatch.setenv("PORT", "1234")
        monkeypatch.setenv("RELOAD", "false")

        main.run()

        assert calls["port"] == 1234
        assert calls["reload"] is False

    def test_get_artifact_refresh_interval_seconds_default(self, monkeypatch):
        monkeypatch.delenv("ARTIFACT_REFRESH_INTERVAL_SECONDS", raising=False)
        assert main.get_artifact_refresh_interval_seconds() == 5.0

    def test_get_artifact_refresh_interval_seconds_invalid(self, monkeypatch):
        monkeypatch.setenv("ARTIFACT_REFRESH_INTERVAL_SECONDS", "invalid")
        assert main.get_artifact_refresh_interval_seconds() == 5.0

    def test_get_artifact_refresh_interval_seconds_positive(self, monkeypatch):
        monkeypatch.setenv("ARTIFACT_REFRESH_INTERVAL_SECONDS", "2.5")
        assert main.get_artifact_refresh_interval_seconds() == 2.5

    def test_get_artifact_refresh_interval_seconds_non_positive(self, monkeypatch):
        monkeypatch.setenv("ARTIFACT_REFRESH_INTERVAL_SECONDS", "0")
        assert main.get_artifact_refresh_interval_seconds() == 5.0

    def test_preload_recommendation_artifacts(self):
        with patch(
            "backend.routes.recommend.get_recommend_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.refresh_bundle.return_value = True
            mock_get_service.return_value = mock_service

            main.preload_recommendation_artifacts()

            mock_service.refresh_bundle.assert_called_once()

    def test_preload_recommendation_artifacts_when_nothing_to_load(self):
        with patch(
            "backend.routes.recommend.get_recommend_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.refresh_bundle.return_value = False
            mock_get_service.return_value = mock_service

            main.preload_recommendation_artifacts()

            mock_service.refresh_bundle.assert_called_once()

    def test_preload_recommendation_artifacts_handles_refresh_error(self):
        with patch(
            "backend.routes.recommend.get_recommend_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.refresh_bundle.side_effect = Exception("refresh failed")
            mock_get_service.return_value = mock_service

            main.preload_recommendation_artifacts()

            mock_service.refresh_bundle.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_recommendation_artifacts_refreshes_until_cancelled(self):
        with patch(
            "backend.routes.recommend.get_recommend_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            async def fake_sleep(_):
                raise asyncio.CancelledError()

            with patch("backend.main.asyncio.sleep", side_effect=fake_sleep):
                with pytest.raises(asyncio.CancelledError):
                    await main.watch_recommendation_artifacts(poll_interval=0.01)

            mock_service.refresh_bundle.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_recommendation_artifacts_handles_refresh_error(self):
        with patch(
            "backend.routes.recommend.get_recommend_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.refresh_bundle.side_effect = Exception("refresh failed")
            mock_get_service.return_value = mock_service

            async def fake_sleep(_):
                raise asyncio.CancelledError()

            with patch("backend.main.asyncio.sleep", side_effect=fake_sleep):
                with pytest.raises(asyncio.CancelledError):
                    await main.watch_recommendation_artifacts(poll_interval=0.01)

            mock_service.refresh_bundle.assert_called_once()

    def test_get_recommend_service_state_unloaded(self):
        import backend.routes.recommend as recommend_routes

        recommend_routes._service_instance = None
        assert recommend_routes.get_recommend_service_state() == {
            "loaded_in_memory": False,
            "run_id": None,
        }

    def test_get_recommend_service_state_loaded(self):
        import backend.routes.recommend as recommend_routes

        mock_service = MagicMock()
        mock_service._bundle = object()
        mock_service._cached_version = "run-123"
        recommend_routes._service_instance = mock_service

        assert recommend_routes.get_recommend_service_state() == {
            "loaded_in_memory": True,
            "run_id": "run-123",
        }
        recommend_routes._service_instance = None

    def test_ml_status_ready(self, client):
        with (
            patch("ml.registry.ModelRegistry") as mock_reg_class,
            patch(
                "backend.routes.recommend.get_recommend_service_state"
            ) as mock_service_state,
        ):
            mock_reg = MagicMock()
            mock_version = MagicMock()
            mock_version.run_id = "test-run-123"
            mock_version.timestamp = 1000.0
            mock_reg.get_current_version.return_value = mock_version
            mock_reg_class.return_value = mock_reg
            mock_service_state.return_value = {
                "loaded_in_memory": False,
                "run_id": None,
            }

            r = client.get("/ml-status")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "ready"
            assert data["run_id"] == "test-run-123"
            assert data["loaded_in_memory"] is False

    def test_ml_status_loaded_in_memory(self, client):
        with (
            patch("ml.registry.ModelRegistry") as mock_reg_class,
            patch(
                "backend.routes.recommend.get_recommend_service_state"
            ) as mock_service_state,
        ):
            mock_reg = MagicMock()
            mock_version = MagicMock()
            mock_version.run_id = "test-run-123"
            mock_version.timestamp = 1000.0
            mock_reg.get_current_version.return_value = mock_version
            mock_reg_class.return_value = mock_reg
            mock_service_state.return_value = {
                "loaded_in_memory": True,
                "run_id": "test-run-123",
            }

            r = client.get("/ml-status")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "ready"
            assert data["loaded_in_memory"] is True

    def test_ml_status_missing(self, client):
        with patch("ml.registry.ModelRegistry") as mock_reg_class:
            mock_reg = MagicMock()
            mock_reg.get_current_version.return_value = None
            mock_reg_class.return_value = mock_reg

            r = client.get("/ml-status")
            assert r.status_code == 200
            assert r.json()["status"] == "missing_artifacts"
            assert r.json()["loaded_in_memory"] is False

    def test_ml_status_error(self, client):
        with patch("ml.registry.ModelRegistry", side_effect=Exception("DB Error")):
            r = client.get("/ml-status")
            assert r.status_code == 200
            assert r.json()["status"] == "error"
            assert r.json()["loaded_in_memory"] is False

    def test_v1_version_fallback(self, client):
        with patch("backend.routes.router.get_registry") as mock_get_reg:
            mock_registry = MagicMock()
            mock_registry.get_current_version.return_value = None
            mock_get_reg.return_value = mock_registry

            # Force the registry instance to reset
            import backend.routes.router as vr

            vr._registry_instance = None

            r = client.get("/v1/version")
            assert r.status_code == 200
            data = r.json()
            assert data["version"] == "0.1.0"
            assert data["run_id"] == "unknown"

    def test_version_endpoints_success(self, client):
        # Test root version success path
        with patch("ml.registry.ModelRegistry") as mock_reg_class:
            mock_registry = MagicMock()
            mock_vinfo = MagicMock()
            mock_vinfo.version = "v1.2.3"
            mock_vinfo.run_id = "run_99"
            mock_vinfo.timestamp = 1000
            mock_registry.get_current_version.return_value = mock_vinfo
            mock_reg_class.return_value = mock_registry

            r = client.get("/version")
            assert r.status_code == 200
            data = r.json()
            assert data["version"] == "1.2.3"

        # Test v1 version success path
        with patch("backend.routes.router.get_registry") as mock_get_reg:
            mock_get_reg.return_value = mock_registry
            r = client.get("/v1/version")
            assert r.status_code == 200
            data = r.json()
            assert data["version"] == "1.2.3"

    @pytest.mark.asyncio
    async def test_explain_endpoint(self, client):
        class MockExplainService:
            async def explain_draft(self, payload):
                from backend.schemas.explain import (
                    ExplainDraftResponse,
                    ChampionExplanation,
                )
                from core.domain.enums import Role

                return ExplainDraftResponse(
                    role=Role.MID,
                    explanations=[
                        ChampionExplanation(champion="Ahri", explanation="Good")
                    ],
                )

        from unittest.mock import patch

        with patch("backend.routes.explain.get_explain_service") as mock_get_svc:
            mock_get_svc.return_value = MockExplainService()

            r = client.post(
                "/v1/explain/draft",
                json={
                    "role": "MID",
                    "recommendations": [
                        {"champion": "Ahri", "allies": [], "enemies": [], "reasons": []}
                    ],
                },
            )
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_recommend_endpoint(self, client):
        import backend.routes.recommend as rr
        from unittest.mock import MagicMock, patch

        class MockRecommendService:
            async def recommend_draft(self, payload):
                from backend.schemas.recommend import (
                    RecommendDraftResponse,
                    Recommendation,
                )
                from core.domain.enums import Role

                return RecommendDraftResponse(
                    role=Role.MID,
                    allies=[],
                    enemies=[],
                    bans=[],
                    recommendations=[
                        Recommendation(
                            champion="Ahri", score=0.8, role="MID", reasons=[]
                        )
                    ],
                )

        # Test the singleton logic before overriding dependency
        rr._service_instance = None
        with patch("backend.routes.router.get_registry") as mock_get_reg:
            mock_get_reg.return_value = MagicMock()
            service_instance = rr.get_recommend_service()
            assert isinstance(service_instance, rr.RecommendService)
            assert rr.get_recommend_service() is service_instance

        client.app.dependency_overrides[rr.get_recommend_service] = lambda: (
            MockRecommendService()
        )

        r = client.post(
            "/v1/recommend/draft",
            json={"role": "MID", "allies": ["Ashe"], "enemies": ["Zed"]},
        )
        assert r.status_code == 200
        client.app.dependency_overrides.clear()

    def test_router_get_registry_singleton(self):
        """Test the router.get_registry explicitly to hit the _registry_instance = None branch"""
        import backend.routes.router as vr
        from unittest.mock import patch, MagicMock

        # Force reset
        vr._registry_instance = None

        # Calling get_registry should instantiate a ModelRegistry initially
        with patch("backend.routes.router.ModelRegistry") as mock_reg_class:
            mock_reg = MagicMock()
            mock_reg_class.return_value = mock_reg

            reg1 = vr.get_registry()
            assert reg1 is mock_reg
            mock_reg_class.assert_called_once()

            # Second call uses singleton value cache without initialization
            reg2 = vr.get_registry()
            assert reg2 is mock_reg
            assert mock_reg_class.call_count == 1
