import pytest
from unittest.mock import Mock, patch, AsyncMock

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


@pytest.mark.asyncio
async def test_recommend_draft_basic(mock_registry):
    config = ScoringConfig()

    service = RecommendService(registry=mock_registry, config=config)

    payload = RecommendDraftRequest(
        role=Role.TOP, allies=["Ahri"], enemies=["Darius"], bans=["Teemo"]
    )

    resp = await service.recommend_draft(payload)

    assert resp.role == Role.TOP
    assert len(resp.recommendations) > 0

    # Aatrox should be in recommendations
    champs = [r.champion for r in resp.recommendations]
    assert "Aatrox" in champs
    assert "Riven" in champs

    # Check explanation format (heuristic)
    top_rec = resp.recommendations[0]
    assert top_rec.explanation is not None
    assert len(top_rec.explanation) > 0


@pytest.mark.asyncio
async def test_recommend_draft_filtering(mock_registry):
    # Filter out taken champs
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    # Assuming Riven is banned
    payload = RecommendDraftRequest(role=Role.TOP, allies=[], enemies=[], bans=["Riven"])

    resp = await service.recommend_draft(payload)
    champs = [r.champion for r in resp.recommendations]
    assert "Riven" not in champs
    assert "Aatrox" in champs


@pytest.mark.asyncio
async def test_recommend_draft_empty_pool(mock_registry):
    # Request for a role with no stats
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    payload = RecommendDraftRequest(
        role=Role.ADC,  # No ADC stats in mock
        allies=[],
        enemies=[],
        bans=[],
    )

    resp = await service.recommend_draft(payload)
    assert len(resp.recommendations) == 0


@pytest.mark.asyncio
async def test_recommend_draft_with_ai_explanations(mock_registry):
    """Test that AI explanations are used when API key is present."""
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    payload = RecommendDraftRequest(role=Role.TOP, allies=["Ahri"], enemies=["Darius"], bans=[])

    # Mock settings to have an API key
    with patch("app.services.recommend_service.settings") as mock_settings:
        mock_settings.genai.api_key = "test-api-key"

        # Mock the AI explanation function
        with patch(
            "app.services.recommend_service.agenerate_ai_explanation", new_callable=AsyncMock
        ) as mock_ai:
            mock_ai.return_value = "AI generated explanation for this champion"

            resp = await service.recommend_draft(payload)

            # Verify AI explanation was called
            assert mock_ai.called
            # Verify response has explanations
            assert len(resp.recommendations) > 0
            assert "AI generated" in resp.recommendations[0].explanation
