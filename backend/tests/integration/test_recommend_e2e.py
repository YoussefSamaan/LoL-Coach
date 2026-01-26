"""Integration tests for the complete recommendation system.

Tests the full flow:
1. Build ML artifacts from parsed data
2. Register model in registry
3. Load model via registry
4. Generate recommendations via API
"""

import json

import pytest

from app.ml.build_tables import build_tables
from app.ml.training import SmoothingConfig
from app.services.model_registry import ModelRegistry
from app.domain.enums import Role


@pytest.fixture
def test_data_dir(tmp_path):
    """Create test data directory with sample matches."""
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()

    # Create sample match data
    matches = [
        {
            "match_id": "match_1",
            "blue_team": json.dumps(
                [
                    {"c": "Ahri", "r": "mid"},
                    {"c": "Amumu", "r": "jungle"},
                    {"c": "Jinx", "r": "adc"},
                    {"c": "Thresh", "r": "support"},
                    {"c": "Darius", "r": "top"},
                ]
            ),
            "red_team": json.dumps(
                [
                    {"c": "Zed", "r": "mid"},
                    {"c": "LeeSin", "r": "jungle"},
                    {"c": "Caitlyn", "r": "adc"},
                    {"c": "Leona", "r": "support"},
                    {"c": "Garen", "r": "top"},
                ]
            ),
            "winner": "BLUE",
        },
        {
            "match_id": "match_2",
            "blue_team": json.dumps(
                [
                    {"c": "Ahri", "r": "mid"},
                    {"c": "Elise", "r": "jungle"},
                    {"c": "Ashe", "r": "adc"},
                    {"c": "Braum", "r": "support"},
                    {"c": "Renekton", "r": "top"},
                ]
            ),
            "red_team": json.dumps(
                [
                    {"c": "Yasuo", "r": "mid"},
                    {"c": "Khazix", "r": "jungle"},
                    {"c": "Vayne", "r": "adc"},
                    {"c": "Nautilus", "r": "support"},
                    {"c": "Malphite", "r": "top"},
                ]
            ),
            "winner": "BLUE",
        },
        {
            "match_id": "match_3",
            "blue_team": json.dumps(
                [
                    {"c": "Syndra", "r": "mid"},
                    {"c": "Jarvan", "r": "jungle"},
                    {"c": "Ezreal", "r": "adc"},
                    {"c": "Lulu", "r": "support"},
                    {"c": "Shen", "r": "top"},
                ]
            ),
            "red_team": json.dumps(
                [
                    {"c": "Ahri", "r": "mid"},
                    {"c": "Amumu", "r": "jungle"},
                    {"c": "Jinx", "r": "adc"},
                    {"c": "Thresh", "r": "support"},
                    {"c": "Darius", "r": "top"},
                ]
            ),
            "winner": "RED",
        },
    ]

    # Write to JSON file
    (parsed_dir / "test_matches.json").write_text(json.dumps(matches), encoding="utf-8")

    return tmp_path


class TestRecommendationSystemE2E:
    """End-to-end tests for the complete recommendation system."""

    def test_full_pipeline(self, test_data_dir, monkeypatch):
        """Test complete flow: build → register → load → recommend."""
        from unittest.mock import MagicMock

        # 1. Setup paths
        artifacts_dir = test_data_dir / "artifacts"

        # Mock settings objects
        mock_settings = MagicMock()
        mock_settings.data_root = test_data_dir
        mock_settings.artifacts_path = artifacts_dir
        mock_settings.ingest.paths.parsed_dir = "parsed"

        # Patch settings in build_tables module
        monkeypatch.setattr("app.ml.build_tables.settings", mock_settings)

        # 2. Build ML artifacts
        config = SmoothingConfig(min_samples=1)  # Low threshold for test data
        run_dir = build_tables(config)

        assert run_dir is not None
        assert run_dir.exists()
        assert (run_dir / "stats.json").exists()
        assert (run_dir / "manifest.json").exists()

        # 3. Register model
        registry = ModelRegistry(artifacts_root=artifacts_dir)
        run_id = run_dir.name
        registry.register(run_id=run_id, version="v1.0.0", metrics={"matches": 3})

        # 4. Verify registration
        current_version = registry.get_current_version()
        assert current_version is not None
        assert current_version.run_id == run_id
        assert current_version.version == "v1.0.0"

        # 5. Load model via registry
        bundle = registry.load_latest()
        assert bundle.stats is not None
        assert bundle.manifest is not None

        # Verify we have stats for champions we trained on
        assert "MID" in bundle.stats.role_strength
        assert "Ahri" in bundle.stats.role_strength["MID"]

        # 6. Test recommendation via service (not API to avoid dependency injection complexity)
        from app.services.recommend_service import RecommendService
        from app.ml.scoring import ScoringConfig
        from app.schemas.recommend import RecommendDraftRequest

        scoring_config = ScoringConfig()
        service = RecommendService(registry=registry, config=scoring_config)

        # Request recommendations for MID with Amumu as ally
        request = RecommendDraftRequest(
            role=Role.MID, allies=["Amumu"], enemies=["Zed"], bans=["Yasuo"], top_k=5
        )

        response = service.recommend_draft(request)

        # Verify response structure
        assert response.role == Role.MID
        assert response.allies == ["Amumu"]
        assert response.enemies == ["Zed"]
        assert len(response.recommendations) > 0

        # Verify recommendations have required fields
        for rec in response.recommendations:
            assert rec.champion is not None
            assert rec.score >= 0
            assert rec.score <= 1
            assert len(rec.reasons) > 0
            assert rec.explanation is not None

        # Ahri should be in recommendations (won 2/3 games, good synergy with Amumu)
        rec_champions = [r.champion for r in response.recommendations]
        assert "Ahri" in rec_champions

    def test_model_rollback(self, test_data_dir, monkeypatch):
        """Test model rollback functionality."""
        from unittest.mock import MagicMock
        from datetime import datetime

        artifacts_dir = test_data_dir / "artifacts"

        # Mock settings objects
        mock_settings = MagicMock()
        mock_settings.data_root = test_data_dir
        mock_settings.artifacts_path = artifacts_dir
        mock_settings.ingest.paths.parsed_dir = "parsed"

        # Patch settings in build_tables module
        monkeypatch.setattr("app.ml.build_tables.settings", mock_settings)

        # Helper to generate unique times
        class MockDatetime:
            def __init__(self, timestamp):
                self._ts = timestamp

            def strftime(self, fmt):
                return datetime.fromtimestamp(self._ts).strftime(fmt)

            @classmethod
            def now(cls):
                return cls(cls._current_ts)

        MockDatetime._current_ts = 1700000000.0

        # Build first model
        MockDatetime._current_ts = 1700000001.0
        monkeypatch.setattr("app.ml.build_tables.datetime", MockDatetime)

        config = SmoothingConfig(min_samples=1)
        run_dir_1 = build_tables(config)

        registry = ModelRegistry(artifacts_root=artifacts_dir)
        run_id_1 = run_dir_1.name
        registry.register(run_id=run_id_1, version="v1.0.0")

        # Build second model (simulate retraining)
        MockDatetime._current_ts = 1700000002.0
        monkeypatch.setattr("app.ml.build_tables.datetime", MockDatetime)

        run_dir_2 = build_tables(config)
        run_id_2 = run_dir_2.name
        registry.register(run_id=run_id_2, version="v1.1.0")

        # Verify v1.1.0 is current
        current = registry.get_current_version()
        assert current.version == "v1.1.0"
        assert current.run_id == run_id_2

        # Rollback to v1.0.0
        registry.rollback()

        # Verify v1.0.0 is now current
        current = registry.get_current_version()
        assert current.version == "v1.0.0"
        assert current.run_id == run_id_1

        # Verify we can still load the model
        bundle = registry.load_latest()
        assert bundle.manifest.run_id == run_id_1

    def test_version_listing(self, test_data_dir, monkeypatch):
        """Test listing all model versions."""
        from unittest.mock import MagicMock
        from datetime import datetime

        artifacts_dir = test_data_dir / "artifacts"

        # Mock settings objects
        mock_settings = MagicMock()
        mock_settings.data_root = test_data_dir
        mock_settings.artifacts_path = artifacts_dir
        mock_settings.ingest.paths.parsed_dir = "parsed"

        # Patch settings in build_tables module
        monkeypatch.setattr("app.ml.build_tables.settings", mock_settings)

        # Helper to generate unique times
        class MockDatetime:
            def __init__(self, timestamp):
                self._ts = timestamp

            def strftime(self, fmt):
                return datetime.fromtimestamp(self._ts).strftime(fmt)

            @classmethod
            def now(cls):
                return cls(cls._current_ts)

        registry = ModelRegistry(artifacts_root=artifacts_dir)

        # Register multiple versions
        config = SmoothingConfig(min_samples=1)

        start_ts = 1700000000.0

        for i, version in enumerate(["v1.0.0", "v1.1.0", "v1.2.0"]):
            MockDatetime._current_ts = start_ts + i
            monkeypatch.setattr("app.ml.build_tables.datetime", MockDatetime)

            run_dir = build_tables(config)
            registry.register(run_id=run_dir.name, version=version, metrics={"iteration": i})

        # List versions
        versions = registry.list_versions()

        assert len(versions) == 3
        # Should be sorted newest first
        assert versions[0].version == "v1.2.0"
        assert versions[1].version == "v1.1.0"
        assert versions[2].version == "v1.0.0"

        # Verify metrics
        assert versions[0].metrics["iteration"] == 2
        assert versions[1].metrics["iteration"] == 1
        assert versions[2].metrics["iteration"] == 0
