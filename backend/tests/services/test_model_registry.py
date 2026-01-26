"""Tests for ModelRegistry with version management and rollback."""

import json
import pytest
from pathlib import Path

from app.services.model_registry import ModelRegistry, VersionInfo, RegistryState
from app.ml.artifacts import ArtifactBundle
from app.ml.training import ArtifactStats, ManifestData


@pytest.fixture
def mock_artifacts_root(tmp_path):
    """Create mock artifacts directory structure."""
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    (artifacts_root / "runs").mkdir()
    return artifacts_root


@pytest.fixture
def sample_artifact_bundle():
    """Create a sample ArtifactBundle for testing."""
    stats = ArtifactStats(
        role_strength={"MID": {"Ahri": 0.52}},
        synergy={},
        counter={},
        global_winrates={"Ahri": 0.51},
    )
    manifest = ManifestData(
        run_id="test_run", timestamp=1706112000.0, rows_count=1000, source="/test/data"
    )
    return ArtifactBundle(stats=stats, manifest=manifest)


def create_mock_run(artifacts_root: Path, run_id: str, bundle: ArtifactBundle):
    """Helper to create a mock run directory with artifacts."""
    from app.ml.artifacts import save_artifact_bundle

    run_dir = artifacts_root / "runs" / run_id
    save_artifact_bundle(run_dir, bundle)
    return run_dir


class TestModelRegistryBasics:
    """Test basic registry functionality."""

    def test_init_creates_directories(self, mock_artifacts_root):
        """Should create runs directory on init."""
        ModelRegistry(artifacts_root=mock_artifacts_root)
        assert (mock_artifacts_root / "runs").exists()

    def test_load_state_empty(self, mock_artifacts_root):
        """Should return empty state when no registry exists."""
        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        state = registry._load_state()

        assert state.current == ""
        assert state.previous is None
        assert len(state.versions) == 0

    def test_backward_compat_latest_json(self, mock_artifacts_root, sample_artifact_bundle):
        """Should load from latest.json for backward compatibility."""
        # Create run
        create_mock_run(mock_artifacts_root, "run_123", sample_artifact_bundle)

        # Create old-style latest.json (no registry.json)
        (mock_artifacts_root / "latest.json").write_text(
            json.dumps({"run": "run_123"}), encoding="utf-8"
        )

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        bundle = registry.load_latest()

        assert isinstance(bundle, ArtifactBundle)
        assert bundle.stats.role_strength["MID"]["Ahri"] == 0.52


class TestRegisterAndLoad:
    """Test registration and loading of models."""

    def test_register_first_model(self, mock_artifacts_root, sample_artifact_bundle):
        """Should register first model as current."""
        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0", metrics={"rows": 1000})

        state = registry._load_state()
        assert state.current == "run_001"
        assert state.previous is None
        assert "run_001" in state.versions
        assert state.versions["run_001"].version == "v1.0.0"

    def test_register_second_model(self, mock_artifacts_root, sample_artifact_bundle):
        """Should move current to previous when registering new model."""
        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)
        create_mock_run(mock_artifacts_root, "run_002", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0")
        registry.register(run_id="run_002", version="v1.1.0")

        state = registry._load_state()
        assert state.current == "run_002"
        assert state.previous == "run_001"
        assert len(state.versions) == 2

    def test_load_latest_after_register(self, mock_artifacts_root, sample_artifact_bundle):
        """Should load the current registered model."""
        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0")

        bundle = registry.load_latest()
        assert isinstance(bundle, ArtifactBundle)

    def test_load_current_alias(self, mock_artifacts_root, sample_artifact_bundle):
        """load_current() should be an alias for load_latest()."""
        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0")

        bundle1 = registry.load_latest()
        bundle2 = registry.load_current()

        assert bundle1.manifest.run_id == bundle2.manifest.run_id

    def test_load_version_specific(self, mock_artifacts_root, sample_artifact_bundle):
        """Should load a specific version by run_id."""
        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)
        create_mock_run(mock_artifacts_root, "run_002", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0")
        registry.register(run_id="run_002", version="v1.1.0")

        # Load old version explicitly
        bundle = registry.load_version("run_001")
        assert isinstance(bundle, ArtifactBundle)

    def test_load_latest_no_current(self, mock_artifacts_root):
        """Should raise error when no current model exists."""
        registry = ModelRegistry(artifacts_root=mock_artifacts_root)

        with pytest.raises(ValueError, match="No current model registered"):
            registry.load_latest()

    def test_load_version_not_found(self, mock_artifacts_root):
        """Should raise error when version doesn't exist."""
        registry = ModelRegistry(artifacts_root=mock_artifacts_root)

        with pytest.raises(ValueError, match="not found"):
            registry.load_version("nonexistent")


class TestRollback:
    """Test rollback functionality."""

    def test_rollback_success(self, mock_artifacts_root, sample_artifact_bundle):
        """Should rollback to previous version."""
        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)
        create_mock_run(mock_artifacts_root, "run_002", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0")
        registry.register(run_id="run_002", version="v1.1.0")

        # Before rollback
        assert registry._load_state().current == "run_002"

        # Rollback
        registry.rollback()

        # After rollback
        state = registry._load_state()
        assert state.current == "run_001"
        assert state.previous == "run_002"

    def test_rollback_no_previous(self, mock_artifacts_root, sample_artifact_bundle):
        """Should raise error when no previous version exists."""
        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0")

        with pytest.raises(ValueError, match="No previous model"):
            registry.rollback()

    def test_rollback_twice(self, mock_artifacts_root, sample_artifact_bundle):
        """Should be able to rollback multiple times (swap back and forth)."""
        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)
        create_mock_run(mock_artifacts_root, "run_002", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0")
        registry.register(run_id="run_002", version="v1.1.0")

        # Rollback once
        registry.rollback()
        assert registry._load_state().current == "run_001"

        # Rollback again (swap back)
        registry.rollback()
        assert registry._load_state().current == "run_002"


class TestVersionManagement:
    """Test version listing and info retrieval."""

    def test_list_versions_empty(self, mock_artifacts_root):
        """Should return empty list when no versions registered."""
        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        versions = registry.list_versions()

        assert len(versions) == 0

    def test_list_versions_sorted(self, mock_artifacts_root, sample_artifact_bundle):
        """Should return versions sorted by timestamp (newest first)."""
        import time

        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)
        create_mock_run(mock_artifacts_root, "run_002", sample_artifact_bundle)
        create_mock_run(mock_artifacts_root, "run_003", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0")
        time.sleep(0.01)  # Ensure different timestamps
        registry.register(run_id="run_002", version="v1.1.0")
        time.sleep(0.01)
        registry.register(run_id="run_003", version="v1.2.0")

        versions = registry.list_versions()

        assert len(versions) == 3
        assert versions[0].run_id == "run_003"  # Newest first
        assert versions[1].run_id == "run_002"
        assert versions[2].run_id == "run_001"

    def test_get_current_version(self, mock_artifacts_root, sample_artifact_bundle):
        """Should return info about current version."""
        create_mock_run(mock_artifacts_root, "run_001", sample_artifact_bundle)

        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        registry.register(run_id="run_001", version="v1.0.0", metrics={"rows": 5000})

        current = registry.get_current_version()

        assert current is not None
        assert current.run_id == "run_001"
        assert current.version == "v1.0.0"
        assert current.metrics["rows"] == 5000

    def test_get_current_version_none(self, mock_artifacts_root):
        """Should return None when no current version."""
        registry = ModelRegistry(artifacts_root=mock_artifacts_root)
        current = registry.get_current_version()

        assert current is None


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_version_info_creation(self):
        """Should create VersionInfo with all fields."""
        info = VersionInfo(
            run_id="run_001",
            version="v1.0.0",
            timestamp=1706112000.0,
            metrics={"rows": 1000, "accuracy": 0.85},
        )

        assert info.run_id == "run_001"
        assert info.version == "v1.0.0"
        assert info.metrics["rows"] == 1000

    def test_version_info_immutable(self):
        """VersionInfo should be immutable (frozen)."""
        info = VersionInfo(run_id="run_001", version="v1.0.0", timestamp=1706112000.0)

        with pytest.raises(Exception):  # Pydantic raises ValidationError
            info.run_id = "run_002"

    def test_registry_state_creation(self):
        """Should create RegistryState with all fields."""
        state = RegistryState(
            current="run_002",
            previous="run_001",
            versions={
                "run_001": VersionInfo(run_id="run_001", version="v1.0.0", timestamp=1.0),
                "run_002": VersionInfo(run_id="run_002", version="v1.1.0", timestamp=2.0),
            },
        )

        assert state.current == "run_002"
        assert state.previous == "run_001"
        assert len(state.versions) == 2
