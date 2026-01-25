from fastapi.testclient import TestClient
from unittest.mock import Mock
import pytest

from app.main import app
from app.services.model_registry import ModelRegistry
from app.ml.artifacts import ArtifactBundle
from app.ml.training import ArtifactStats, ManifestData

# We need to override the dependency directly
from app.api.v1.recommend import get_model_registry

client = TestClient(app)


@pytest.fixture
def mock_registry_dependency():
    mock_reg = Mock(spec=ModelRegistry)
    
    # Create complete ArtifactStats with all required fields
    stats = ArtifactStats(
        role_strength={"MID": {"Ahri": 0.55}},
        synergy={},
        counter={},
        global_winrates={"Ahri": 0.52}
    )
    
    # Create complete ManifestData with all required fields
    manifest = ManifestData(
        run_id="test_run",
        timestamp=1706112000.0,
        rows_count=1000,
        source="/test/data"
    )
    
    mock_reg.load_latest.return_value = ArtifactBundle(stats=stats, manifest=manifest)
    return mock_reg



def test_recommend_endpoint_success(mock_registry_dependency):
    # Override dependency
    app.dependency_overrides[get_model_registry] = lambda: mock_registry_dependency

    payload = {"role": "MID", "allies": ["Ashe"], "enemies": ["Zed"], "bans": []}

    resp = client.post("/v1/recommend/draft", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "MID"
    assert len(data["recommendations"]) > 0
    assert data["recommendations"][0]["champion"] == "Ahri"

    # Cleanup
    app.dependency_overrides = {}


def test_recommend_endpoint_validation_error():
    # Missing required field 'role'
    payload = {"allies": [], "enemies": [], "bans": []}
    resp = client.post("/v1/recommend/draft", json=payload)
    assert resp.status_code == 422
