"""Tests for TableBasedModel."""

import json
from unittest.mock import patch

import pytest

from ml.models.table_based import TableBasedModel
from ml.scoring import ScoringConfig
from ml.training import ArtifactStats
from ml.artifacts.manifest import ArtifactBundle, ManifestData


@pytest.fixture
def mock_stats():
    """Mock ArtifactStats."""
    return ArtifactStats(
        global_winrates={"Ahri": 0.5},
        role_strength={"MID": {"Ahri": 0.52}},
        synergy={},
        counter={},
    )


def test_table_based_model_init(mock_stats):
    """Test initialization."""
    model = TableBasedModel(stats=mock_stats)
    assert model.stats is not None
    assert model.config is not None
    assert model.metadata == {}


def test_table_based_model_train():
    """Test train raises NotImplementedError."""
    model = TableBasedModel()
    with pytest.raises(NotImplementedError):
        model.train(train_data=None)


def test_table_based_model_predict_unloaded():
    """Test predict raises ValueError if not loaded."""
    model = TableBasedModel()
    with pytest.raises(ValueError):
        model.predict(role="MID", allies=[], enemies=[], candidates=["Ahri"])


def test_table_based_model_predict_success(mock_stats):
    """Test successful prediction."""
    model = TableBasedModel(stats=mock_stats)
    predictions = model.predict(
        role="MID",
        allies=[],
        enemies=[],
        candidates=["Ahri"],
    )
    assert len(predictions) == 1
    assert predictions[0].champion == "Ahri"
    assert predictions[0].score > 0
    assert predictions[0].metadata["model_type"] == "table_based"


def test_table_based_model_save_unloaded(tmp_path):
    """Test save raises ValueError if not loaded."""
    model = TableBasedModel()
    with pytest.raises(ValueError):
        model.save(tmp_path)


def test_table_based_model_save_success(mock_stats, tmp_path):
    """Test successful save."""
    model = TableBasedModel(stats=mock_stats, metadata={"foo": "bar"})
    model.save(tmp_path)

    assert (tmp_path / "stats.json").exists()
    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "metadata.json").exists()

    metadata = json.loads((tmp_path / "metadata.json").read_text())
    assert metadata["foo"] == "bar"


@patch("ml.models.table_based.load_artifact_bundle")
def test_table_based_model_load_defaults(mock_load, tmp_path, mock_stats):
    """Test load with missing config and metadata."""
    manifest = ManifestData(
        run_id="test",
        timestamp=1.0,
        source="test",
        config={},
        rows_count=100,
        status="completed",
        metrics={},
        artifact_paths={"stats": "stats.json"},
    )

    mock_load.return_value = ArtifactBundle(manifest=manifest, stats=mock_stats)

    model = TableBasedModel.load(tmp_path)

    assert model.stats == mock_stats
    assert isinstance(model.config, ScoringConfig)
    assert model.metadata == {}


@patch("ml.models.table_based.load_artifact_bundle")
def test_table_based_model_load_existing(mock_load, tmp_path, mock_stats):
    """Test load with existing config and metadata."""
    manifest = ManifestData(
        run_id="test",
        timestamp=1.0,
        source="test",
        config={},
        rows_count=100,
        status="completed",
        metrics={},
        artifact_paths={"stats": "stats.json"},
    )

    mock_load.return_value = ArtifactBundle(manifest=manifest, stats=mock_stats)

    (tmp_path / "config.json").write_text(ScoringConfig().model_dump_json())
    (tmp_path / "metadata.json").write_text(json.dumps({"loaded": True}))

    model = TableBasedModel.load(tmp_path)

    assert model.metadata["loaded"] is True


def test_table_based_model_get_info(mock_stats):
    """Test get_model_info."""
    model = TableBasedModel(stats=mock_stats, metadata={"custom": "val"})
    info = model.get_model_info()

    assert info["model_type"] == "table_based"
    assert info["num_champions"] == 1
    assert info["num_roles"] == 1
    assert info["custom"] == "val"
