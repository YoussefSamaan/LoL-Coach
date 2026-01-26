import pytest
from unittest.mock import Mock, patch

from app.services.recommend_service import RecommendService
from app.ml.scoring import ScoringConfig
from app.ml.artifacts import ArtifactBundle
from app.ml.training import ArtifactStats, ManifestData
from app.domain.enums import Role
from app.schemas.recommend import RecommendDraftRequest


@pytest.fixture
def mock_registry():
    registry = Mock()

    # Create complete ArtifactStats with all required fields
    stats = ArtifactStats(
        role_strength={"TOP": {"Aatrox": 0.52, "Riven": 0.50}, "JUNGLE": {"LeeSin": 0.51}},
        synergy={},
        counter={},
        global_winrates={"Aatrox": 0.51, "Riven": 0.49, "LeeSin": 0.50},
    )

    # Create complete ManifestData with all required fields
    manifest = ManifestData(
        run_id="test_run", timestamp=1706112000.0, rows_count=5000, source="/test/data"
    )

    registry.load_latest.return_value = ArtifactBundle(stats=stats, manifest=manifest)
    return registry


@patch("app.services.recommend_service.generate_ai_explanation")
def test_recommend_draft_basic(mock_genai, mock_registry):
    mock_genai.side_effect = lambda champion, **kwargs: f"Mock explanation for {champion}"
    config = ScoringConfig()

    service = RecommendService(registry=mock_registry, config=config)

    payload = RecommendDraftRequest(
        role=Role.TOP, allies=["Ahri"], enemies=["Darius"], bans=["Teemo"]
    )

    resp = service.recommend_draft(payload)

    assert resp.role == Role.TOP
    assert len(resp.recommendations) > 0

    # Aatrox should be in recommendations
    champs = [r.champion for r in resp.recommendations]
    assert "Aatrox" in champs
    assert "Riven" in champs

    # Check explanation format
    top_rec = resp.recommendations[0]
    assert f"Mock explanation for {top_rec.champion}" == top_rec.explanation


@patch("app.services.recommend_service.generate_ai_explanation")
def test_recommend_draft_filtering(mock_genai, mock_registry):
    mock_genai.return_value = "Mock explanation"
    # Filter out taken champs
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    # Assuming Riven is banned
    payload = RecommendDraftRequest(role=Role.TOP, allies=[], enemies=[], bans=["Riven"])

    resp = service.recommend_draft(payload)
    champs = [r.champion for r in resp.recommendations]
    assert "Riven" not in champs
    assert "Aatrox" in champs


@patch("app.services.recommend_service.generate_ai_explanation")
def test_recommend_draft_empty_pool(mock_genai, mock_registry):
    mock_genai.return_value = "Mock explanation"
    # Request for a role with no stats
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    payload = RecommendDraftRequest(
        role=Role.ADC,  # No ADC stats in mock
        allies=[],
        enemies=[],
        bans=[],
    )

    resp = service.recommend_draft(payload)
    assert len(resp.recommendations) == 0
