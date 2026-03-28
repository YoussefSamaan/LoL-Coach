"""Tests for Model Registry."""

import json
from unittest.mock import patch, MagicMock

import pytest

from ml.registry import ModelRegistry
from ml.artifacts.manifest import ArtifactBundle


@pytest.fixture
def registry_dir(tmp_path):
    root = tmp_path / "artifacts"
    root.mkdir()
    return root


@pytest.fixture
def registry(registry_dir):
    return ModelRegistry(artifacts_root=registry_dir)


def test_registry_init(registry_dir, registry):
    assert registry._artifacts_root == registry_dir
    assert registry._registry_file == registry_dir / "registry.json"
    assert registry._runs_dir == registry_dir / "runs"
    assert registry._runs_dir.exists()


def test_load_state_empty(registry):
    state = registry._load_state()
    assert state.current == ""
    assert state.previous is None
    assert state.versions == {}


def test_load_state_from_latest_json(registry, registry_dir):
    latest = registry_dir / "latest.json"
    latest.write_text(json.dumps({"run": "run_1"}))

    state = registry._load_state()
    assert state.current == "run_1"
    assert "run_1" in state.versions


def test_load_state_from_latest_json_empty(registry, registry_dir):
    latest = registry_dir / "latest.json"
    latest.write_text(json.dumps({}))

    state = registry._load_state()
    assert state.current == ""


def test_load_state_from_registry_json(registry, registry_dir):
    registry_file = registry_dir / "registry.json"
    registry_file.write_text(
        json.dumps(
            {
                "current": "run_2",
                "previous": "run_1",
                "versions": {
                    "run_2": {
                        "run_id": "run_2",
                        "version": "v2",
                        "timestamp": 2.0,
                        "metrics": {},
                    }
                },
            }
        )
    )

    state = registry._load_state()
    assert state.current == "run_2"
    assert state.previous == "run_1"


def test_register_new_model(registry):
    registry.register("run_1", "v1", {"acc": 1.0})
    state = registry._load_state()
    assert state.current == "run_1"
    assert state.previous is None
    assert "run_1" in state.versions

    registry.register("run_2", "v2")
    state = registry._load_state()
    assert state.current == "run_2"
    assert state.previous == "run_1"


def test_register_current_run_updates_without_changing_previous(registry):
    registry.register("run_1", "v1.0.0")
    registry.register("run_1", "v1.0.1", {"rows": 10})

    state = registry._load_state()
    assert state.current == "run_1"
    assert state.previous is None
    assert state.versions["run_1"].version == "v1.0.1"
    assert state.versions["run_1"].metrics["rows"] == 10


@patch("ml.registry.load_artifact_bundle")
def test_load_latest(mock_load, registry):
    mock_bundle = MagicMock(spec=ArtifactBundle)
    mock_load.return_value = mock_bundle

    registry.register("run_1", "v1")

    # Needs a real mock dir because load_version uses actual pathlib methods
    # to check if run_dir exists
    with patch("pathlib.Path.exists", return_value=True):
        bundle = registry.load_latest()
        assert bundle == mock_bundle

        # Test alias
        bundle_cur = registry.load_current()
        assert bundle_cur == mock_bundle


def test_load_latest_empty(registry):
    with pytest.raises(ValueError, match="No current model registered"):
        registry.load_latest()


def test_load_version_not_found(registry):
    with pytest.raises(ValueError, match="Model version run_x not found"):
        registry.load_version("run_x")


def test_rollback(registry):
    registry.register("run_1", "v1")
    registry.register("run_2", "v2")

    state = registry._load_state()
    assert state.current == "run_2"

    registry.rollback()

    state = registry._load_state()
    assert state.current == "run_1"
    assert state.previous == "run_2"


def test_rollback_empty(registry):
    with pytest.raises(ValueError, match="No previous model to rollback to"):
        registry.rollback()


def test_list_versions(registry):
    registry.register("run_1", "v1")
    registry.register("run_2", "v2")

    versions = registry.list_versions()
    assert len(versions) == 2
    assert versions[0].run_id == "run_2"  # sorted descending by timestamp


def test_get_current_version(registry):
    assert registry.get_current_version() is None

    registry.register("run_1", "v1")
    v = registry.get_current_version()
    assert v.run_id == "run_1"


def test_next_version(registry):
    assert registry.next_version() == "v1.0.0"

    registry.register("run_1", "v1.0.0")
    assert registry.next_version() == "v1.0.1"

    registry.register("run_2", "v1.2.9")
    assert registry.next_version() == "v1.2.10"
