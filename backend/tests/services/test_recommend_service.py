import pytest
from unittest.mock import Mock, MagicMock

from fastapi import HTTPException
from backend.services.recommend_service import RecommendService
from ml.scoring import ScoringConfig
from ml.artifacts.manifest import ArtifactBundle
from ml.training import ArtifactStats, ManifestData
from core.domain.enums import Role
from backend.schemas.recommend import RecommendDraftRequest


@pytest.fixture
def mock_registry():
    registry = Mock()

    # Create complete ArtifactStats with all required fields
    stats = ArtifactStats(
        role_strength={
            "TOP": {"Aatrox": 0.52, "Riven": 0.50},
            "JUNGLE": {"LeeSin": 0.51},
        },
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

    # Check explanation is empty (use /v1/explain/draft for explanations)
    top_rec = resp.recommendations[0]
    assert top_rec.explanation == ""


@pytest.mark.asyncio
async def test_recommend_draft_filtering(mock_registry):
    # Filter out taken champs
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    # Assuming Riven is banned
    payload = RecommendDraftRequest(
        role=Role.TOP, allies=[], enemies=[], bans=["Riven"]
    )

    resp = await service.recommend_draft(payload)
    champs = [r.champion for r in resp.recommendations]
    assert "Riven" not in champs
    assert "Aatrox" in champs


@pytest.mark.asyncio
async def test_get_bundle_fresh_load(mock_registry):
    mock_bundle = MagicMock()
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    # Setup version info
    v_info = MagicMock()
    v_info.run_id = "v2"
    mock_registry.get_current_version.return_value = v_info
    mock_registry.load_latest.return_value = mock_bundle

    # First call - should load
    bundle1 = service.get_bundle()
    assert bundle1 is mock_bundle
    assert service._cached_version == "v2"
    mock_registry.load_latest.assert_called_once()

    # Second call - should use cache
    bundle2 = service.get_bundle()
    assert bundle2 is mock_bundle
    assert mock_registry.load_latest.call_count == 1


def test_get_bundle_reloads_when_registry_version_changes(mock_registry):
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    first_version = MagicMock()
    first_version.run_id = "v1"
    second_version = MagicMock()
    second_version.run_id = "v2"

    first_bundle = MagicMock()
    second_bundle = MagicMock()

    mock_registry.get_current_version.side_effect = [
        first_version,
        second_version,
    ]
    mock_registry.load_latest.side_effect = [first_bundle, second_bundle]

    assert service.get_bundle() is first_bundle
    assert service._cached_version == "v1"

    assert service.get_bundle() is second_bundle
    assert service._cached_version == "v2"
    assert mock_registry.load_latest.call_count == 2


def test_refresh_bundle_returns_false_when_registry_empty(mock_registry):
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    mock_registry.get_current_version.return_value = None

    assert service.refresh_bundle() is False
    mock_registry.load_latest.assert_not_called()


def test_get_bundle_no_version(mock_registry):
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    mock_registry.get_current_version.return_value = None
    with pytest.raises(HTTPException) as exc:
        service.get_bundle()
    assert exc.value.status_code == 503
    assert "missing" in str(exc.value.detail).lower()


def test_get_bundle_load_error(mock_registry):
    config = ScoringConfig()
    service = RecommendService(registry=mock_registry, config=config)

    v_info = MagicMock()
    v_info.run_id = "v2"
    mock_registry.get_current_version.return_value = v_info
    mock_registry.load_latest.side_effect = Exception("DB crash")

    with pytest.raises(HTTPException) as exc:
        service.get_bundle()
    assert exc.value.status_code == 503
    assert "DB crash" in str(exc.value.detail)


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
