"""Tests for artifact loading and saving."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ml.artifacts import ArtifactBundle, load_artifact_bundle, save_artifact_bundle
from app.ml.training import ArtifactStats, ManifestData, LiftStat


class TestArtifactBundle:
    """Tests for ArtifactBundle model."""

    def test_create_bundle(self):
        """Should create valid bundle with Pydantic models."""
        stats = ArtifactStats(
            role_strength={"MID": {"Ahri": 0.52}},
            synergy={"Ahri": {"Amumu": LiftStat(lift=0.03, count=50)}},
            counter={"Ahri": {"Zed": LiftStat(lift=-0.02, count=75)}},
            global_winrates={"Ahri": 0.52},
        )
        manifest = ManifestData(
            run_id="20260124_120000", timestamp=1706112000.0, rows_count=5000, source="/data/parsed"
        )

        bundle = ArtifactBundle(stats=stats, manifest=manifest)

        assert bundle.stats.global_winrates["Ahri"] == 0.52
        assert bundle.manifest.run_id == "20260124_120000"

    def test_bundle_immutability(self):
        """Bundle should be immutable."""
        stats = ArtifactStats(role_strength={}, synergy={}, counter={}, global_winrates={})
        manifest = ManifestData(run_id="test", timestamp=1.0, rows_count=100, source="/data")

        bundle = ArtifactBundle(stats=stats, manifest=manifest)

        with pytest.raises(ValidationError):
            bundle.stats = stats  # type: ignore


class TestSaveAndLoad:
    """Tests for save_artifact_bundle and load_artifact_bundle."""

    def test_save_and_load_round_trip(self, tmp_path: Path):
        """Should save and load artifacts correctly."""
        stats = ArtifactStats(
            role_strength={"TOP": {"Aatrox": 0.52}, "MID": {"Ahri": 0.51}},
            synergy={"Aatrox": {"Amumu": LiftStat(lift=0.03, count=50)}},
            counter={"Ahri": {"Zed": LiftStat(lift=-0.02, count=75)}},
            global_winrates={"Aatrox": 0.50, "Ahri": 0.505},
        )
        manifest = ManifestData(
            run_id="20260124_120000",
            timestamp=1706112000.0,
            rows_count=5000,
            source="/data/parsed",
            config={"smoothing": "Beta(5,5)"},
            data_quality={"malformed_count": 10},
            artifact_stats={"synergy_pairs": 1500},
        )
        bundle = ArtifactBundle(stats=stats, manifest=manifest)

        run_dir = tmp_path / "run_1"

        # Save
        save_artifact_bundle(run_dir, bundle)

        assert (run_dir / "stats.json").exists()
        assert (run_dir / "manifest.json").exists()

        # Load
        loaded = load_artifact_bundle(run_dir)

        # Verify stats
        assert loaded.stats.role_strength == stats.role_strength
        assert loaded.stats.global_winrates == stats.global_winrates
        assert loaded.stats.synergy["Aatrox"]["Amumu"].lift == 0.03
        assert loaded.stats.synergy["Aatrox"]["Amumu"].count == 50
        assert loaded.stats.counter["Ahri"]["Zed"].lift == -0.02

        # Verify manifest
        assert loaded.manifest.run_id == manifest.run_id
        assert loaded.manifest.rows_count == manifest.rows_count
        assert loaded.manifest.config["smoothing"] == "Beta(5,5)"

    def test_save_creates_directory(self, tmp_path: Path):
        """Should create directory if it doesn't exist."""
        stats = ArtifactStats(role_strength={}, synergy={}, counter={}, global_winrates={})
        manifest = ManifestData(run_id="test", timestamp=1.0, rows_count=100, source="/data")
        bundle = ArtifactBundle(stats=stats, manifest=manifest)

        run_dir = tmp_path / "nested" / "dir" / "run_1"

        save_artifact_bundle(run_dir, bundle)

        assert run_dir.exists()
        assert (run_dir / "stats.json").exists()

    def test_load_missing_stats_file(self, tmp_path: Path):
        """Should raise FileNotFoundError if stats.json missing."""
        run_dir = tmp_path / "run_1"
        run_dir.mkdir()

        # Create only manifest
        (run_dir / "manifest.json").write_text("{}")

        with pytest.raises(FileNotFoundError) as exc_info:
            load_artifact_bundle(run_dir)
        assert "stats.json" in str(exc_info.value).lower()

    def test_load_missing_manifest_file(self, tmp_path: Path):
        """Should raise FileNotFoundError if manifest.json missing."""
        run_dir = tmp_path / "run_1"
        run_dir.mkdir()

        # Create only stats
        (run_dir / "stats.json").write_text("{}")

        with pytest.raises(FileNotFoundError) as exc_info:
            load_artifact_bundle(run_dir)
        assert "manifest.json" in str(exc_info.value).lower()

    def test_load_invalid_json(self, tmp_path: Path):
        """Should raise JSONDecodeError for malformed JSON."""
        run_dir = tmp_path / "run_1"
        run_dir.mkdir()

        (run_dir / "stats.json").write_text("not valid json{")
        (run_dir / "manifest.json").write_text("{}")

        with pytest.raises(json.JSONDecodeError):
            load_artifact_bundle(run_dir)

    def test_load_invalid_schema(self, tmp_path: Path):
        """Should raise ValidationError for invalid data schema."""
        run_dir = tmp_path / "run_1"
        run_dir.mkdir()

        # Invalid: missing required fields
        (run_dir / "stats.json").write_text(
            json.dumps(
                {
                    "role_strength": {},
                    "synergy": {},
                    "counter": {},
                    # Missing global_winrates
                }
            )
        )
        (run_dir / "manifest.json").write_text(
            json.dumps({"run_id": "test", "timestamp": 1.0, "rows_count": 100, "source": "/data"})
        )

        with pytest.raises(ValidationError):
            load_artifact_bundle(run_dir)

    def test_saved_json_is_formatted(self, tmp_path: Path):
        """Saved JSON should be formatted and sorted."""
        stats = ArtifactStats(
            role_strength={"MID": {"Ahri": 0.52}},
            synergy={},
            counter={},
            global_winrates={"Ahri": 0.52},
        )
        manifest = ManifestData(run_id="test", timestamp=1.0, rows_count=100, source="/data")
        bundle = ArtifactBundle(stats=stats, manifest=manifest)

        run_dir = tmp_path / "run_1"
        save_artifact_bundle(run_dir, bundle)

        # Check formatting
        stats_text = (run_dir / "stats.json").read_text()
        assert "\n" in stats_text  # Has newlines (formatted)
        assert "  " in stats_text  # Has indentation

        # Check it's valid JSON
        parsed = json.loads(stats_text)
        assert "global_winrates" in parsed
