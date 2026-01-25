"""Tests for ManifestData model."""

import pytest
from pydantic import ValidationError

from app.ml.training import ManifestData


class TestManifestData:
    """Tests for ManifestData model."""

    def test_valid_manifest(self):
        """Valid ManifestData should be created successfully."""
        manifest = ManifestData(
            run_id="20260124_120000",
            version="v1.0.0",
            timestamp=1706112000.0,
            rows_count=5000,
            source="/data/parsed",
        )

        assert manifest.run_id == "20260124_120000"
        assert manifest.version == "v1.0.0"
        assert manifest.timestamp == 1706112000.0
        assert manifest.rows_count == 5000
        assert manifest.source == "/data/parsed"

    def test_default_version(self):
        """Default version should be v1.0.0."""
        manifest = ManifestData(run_id="test", timestamp=1.0, rows_count=100, source="/data")
        assert manifest.version == "v1.0.0"

    def test_zero_rows_count(self):
        """rows_count = 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ManifestData(run_id="test", timestamp=1.0, rows_count=0, source="/data")
        assert "greater than 0" in str(exc_info.value)

    def test_negative_rows_count(self):
        """Negative rows_count should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ManifestData(run_id="test", timestamp=1.0, rows_count=-100, source="/data")
        assert "greater than 0" in str(exc_info.value)

    def test_optional_fields(self):
        """Optional fields should have default empty dicts."""
        manifest = ManifestData(run_id="test", timestamp=1.0, rows_count=100, source="/data")
        assert manifest.config == {}
        assert manifest.data_quality == {}
        assert manifest.artifact_stats == {}

    def test_with_metadata(self):
        """Manifest with full metadata should work."""
        manifest = ManifestData(
            run_id="20260124_120000",
            timestamp=1706112000.0,
            rows_count=5000,
            source="/data/parsed",
            config={"smoothing": "Beta(5,5)", "min_samples": 5},
            data_quality={"malformed_count": 10, "skipped_pct": 0.2},
            artifact_stats={"synergy_pairs": 1500, "counter_pairs": 1500},
        )

        assert manifest.config["smoothing"] == "Beta(5,5)"
        assert manifest.data_quality["malformed_count"] == 10
        assert manifest.artifact_stats["synergy_pairs"] == 1500
