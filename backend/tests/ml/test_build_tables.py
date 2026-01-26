"""Tests for ML training pipeline (build_tables)."""

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from app.ml.build_tables import (
    build_tables,
    compute_counter,
    compute_role_strength,
    compute_synergy,
)
from app.ml.training import SmoothingConfig


@pytest.fixture
def mock_df():
    """Create mock raw parquet DataFrame."""
    blue = [{"c": "Ahri", "r": "mid"}, {"c": "Amumu", "r": "jungle"}]
    red = [{"c": "Zed", "r": "mid"}, {"c": "LeeSin", "r": "jungle"}]

    data = [
        {
            "match_id": "m1",
            "blue_team": json.dumps(blue),
            "red_team": json.dumps(red),
            "winner": "BLUE",
        }
    ]
    return pd.DataFrame(data)


class TestComputeFunctions:
    """Tests for individual compute functions."""

    def test_compute_role_strength(self):
        """Should compute role-specific winrates with smoothing."""
        # 3 games for Ahri in MID: 2 wins, 1 loss
        # With Beta(5,5): (2+5)/(3+5+5) = 7/13 ≈ 0.538
        data = [
            {"target_role": "MID", "champ": "Ahri", "win": True},
            {"target_role": "MID", "champ": "Ahri", "win": False},
            {"target_role": "MID", "champ": "Ahri", "win": True},
        ]
        df = pd.DataFrame(data)
        config = SmoothingConfig()

        rs = compute_role_strength(df, config)

        assert "MID" in rs
        assert "Ahri" in rs["MID"]
        assert abs(rs["MID"]["Ahri"] - 0.538) < 0.01

    def test_compute_synergy(self):
        """Should compute synergy lifts with sample counts."""
        # Ahri + Amumu: 1 win, 1 loss
        # Pair winrate with Beta(10,10): (1+10)/(2+10+10) = 11/22 = 0.5
        # Global Ahri: (2+5)/(3+5+5) = 7/13 ≈ 0.538
        # Lift: 0.5 - 0.538 ≈ -0.038
        data = [
            {"champ": "Ahri", "win": True, "allies": ["Amumu"]},
            {"champ": "Ahri", "win": False, "allies": ["Amumu"]},
            {"champ": "Ahri", "win": True, "allies": ["Amumu"]},
            {"champ": "Ahri", "win": True, "allies": ["Amumu"]},
            {"champ": "Ahri", "win": False, "allies": ["Amumu"]},
            {"champ": "Ahri", "win": True, "allies": ["Jinx"]},
        ]
        df = pd.DataFrame(data)
        global_wr = {"Ahri": 0.5625}
        config = SmoothingConfig(min_samples=5)

        syn = compute_synergy(df, global_wr, config)

        assert "Ahri" in syn
        assert "Amumu" in syn["Ahri"]
        assert syn["Ahri"]["Amumu"].count == 5
        assert abs(syn["Ahri"]["Amumu"].lift - (-0.0425)) < 0.01

    def test_compute_counter(self):
        """Should compute counter lifts with sample counts."""
        # Ahri vs Zed: 2 wins, 1 loss
        # Matchup winrate with Beta(10,10): (2+10)/(3+10+10) = 12/23 ≈ 0.522
        # Global Ahri: 0.538
        # Lift: 0.522 - 0.538 ≈ -0.016
        data = [
            {"champ": "Ahri", "win": True, "enemies": ["Zed"]},
            {"champ": "Ahri", "win": False, "enemies": ["Zed"]},
            {"champ": "Ahri", "win": True, "enemies": ["Zed"]},
        ]
        df = pd.DataFrame(data)
        global_wr = {"Ahri": 0.538}
        config = SmoothingConfig(min_samples=3)

        ctr = compute_counter(df, global_wr, config)

        assert "Ahri" in ctr
        assert "Zed" in ctr["Ahri"]
        assert ctr["Ahri"]["Zed"].count == 3
        assert abs(ctr["Ahri"]["Zed"].lift - (-0.016)) < 0.02

    def test_compute_counter_min_samples_filter(self):
        """Should filter out pairs below min_samples threshold."""
        # Ahri vs Zed: only 2 games (below min_samples=5)
        data = [
            {"champ": "Ahri", "win": True, "enemies": ["Zed"]},
            {"champ": "Ahri", "win": False, "enemies": ["Zed"]},
        ]
        df = pd.DataFrame(data)
        global_wr = {"Ahri": 0.5}
        config = SmoothingConfig(min_samples=5)

        ctr = compute_counter(df, global_wr, config)

        # Should be empty or Ahri should not have Zed
        if "Ahri" in ctr:
            assert "Zed" not in ctr["Ahri"]


class TestBuildTables:
    """Tests for main build_tables function."""

    @patch("app.ml.build_tables.settings")
    @patch("app.ml.build_tables.save_artifact_bundle")
    def test_build_tables_integration(self, mock_save, mock_settings, tmp_path: Path):
        """Should process data and save artifacts."""
        # Setup
        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"
        mock_settings.artifacts_path = tmp_path / "artifacts"
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir()

        # Create JSON file with match data
        blue = [{"c": "Ahri", "r": "mid"}, {"c": "Amumu", "r": "jungle"}]
        red = [{"c": "Zed", "r": "mid"}, {"c": "LeeSin", "r": "jungle"}]

        match_data = [
            {
                "match_id": "m1",
                "blue_team": json.dumps(blue),
                "red_team": json.dumps(red),
                "winner": "BLUE",
            }
        ]

        # Write JSON file
        (parsed_dir / "test_matches.json").write_text(json.dumps(match_data), encoding="utf-8")

        # Run with low min_samples to ensure pairs are included
        config = SmoothingConfig(min_samples=1)
        run_dir = build_tables(config)

        # Verify save was called
        assert mock_save.called
        bundle = mock_save.call_args[0][1]

        # Verify bundle structure
        assert bundle.stats is not None
        assert bundle.manifest is not None

        # Verify stats
        assert "MID" in bundle.stats.role_strength
        assert "Ahri" in bundle.stats.role_strength["MID"]

        # Ahri won (1 game): (1+5)/(1+5+5) = 6/11 ≈ 0.545
        ahri_wr = bundle.stats.role_strength["MID"]["Ahri"]
        assert abs(ahri_wr - 0.545) < 0.01

        # Verify synergy exists
        assert "Ahri" in bundle.stats.synergy
        assert "Amumu" in bundle.stats.synergy["Ahri"]
        assert bundle.stats.synergy["Ahri"]["Amumu"].count == 1

        # Verify counter exists
        assert "Ahri" in bundle.stats.counter
        assert "Zed" in bundle.stats.counter["Ahri"]

        # Verify manifest
        assert bundle.manifest.rows_count == 4  # 2 blue + 2 red participants
        assert bundle.manifest.run_id is not None
        assert "smoothing" in bundle.manifest.config

        # Verify run_dir was returned
        assert run_dir is not None

    @patch("app.ml.build_tables.settings")
    def test_build_tables_empty_dataframe(self, mock_settings, tmp_path: Path):
        """Should handle empty DataFrame gracefully."""
        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir()

        # Empty list in JSON
        (parsed_dir / "matches.json").write_text("[]")

        result = build_tables()

        assert result is None  # Should return None for empty data

    @patch("app.ml.build_tables.settings")
    def test_build_tables_missing_directory(self, mock_settings, tmp_path: Path):
        """Should handle missing parsed directory."""
        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "nowhere"

        result = build_tables()

        assert result is None

    @patch("app.ml.build_tables.settings")
    @patch("app.ml.build_tables.save_artifact_bundle")
    def test_build_tables_malformed_data(self, mock_save, mock_settings, tmp_path: Path):
        """Should skip malformed rows and continue."""
        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir()

        # Data with bad JSON string for teams
        match_data = [
            {"match_id": "m1", "blue_team": "bad_json", "red_team": "[]", "winner": "BLUE"}
        ]
        (parsed_dir / "matches.json").write_text(json.dumps(match_data))

        result = build_tables()

        # Should return None because no valid participants
        assert result is None
        mock_save.assert_not_called()

    @patch("app.ml.build_tables.settings")
    def test_build_tables_read_error(self, mock_settings, tmp_path: Path):
        """Should handle file read errors gracefully."""
        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir()

        # Create a file
        f = parsed_dir / "test.json"
        f.touch()

        # Mock pathlib.Path.read_text to raise exception
        with patch("pathlib.Path.read_text", side_effect=OSError("Read failed")):
            result = build_tables()

        assert result is None

    @patch("app.ml.build_tables.settings")
    @patch("app.ml.build_tables.save_artifact_bundle")
    def test_build_tables_with_custom_config(self, mock_save, mock_settings, tmp_path: Path):
        """Should use custom smoothing config."""
        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"
        mock_settings.artifacts_path = tmp_path / "artifacts"
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir()

        blue = [{"c": "Ahri", "r": "mid"}]
        red = [{"c": "Zed", "r": "mid"}]

        match_data = [
            {
                "match_id": "m1",
                "blue_team": json.dumps(blue),
                "red_team": json.dumps(red),
                "winner": "BLUE",
            }
        ]

        # Write JSON file
        (parsed_dir / "test_matches.json").write_text(json.dumps(match_data), encoding="utf-8")

        # Custom config with stronger smoothing
        config = SmoothingConfig(role_alpha=10.0, role_beta=10.0, min_samples=1)
        run_dir = build_tables(config)

        assert run_dir is not None
        bundle = mock_save.call_args[0][1]

        # With Beta(10,10): (1+10)/(1+10+10) = 11/21 ≈ 0.524
        ahri_wr = bundle.stats.role_strength["MID"]["Ahri"]
        assert abs(ahri_wr - 0.524) < 0.01

    @patch("app.ml.build_tables.settings")
    @patch("app.ml.build_tables.ArtifactStats")
    def test_build_tables_validation_error(
        self, mock_artifact_stats, mock_settings, tmp_path: Path
    ):
        """Should handle ArtifactStats validation errors gracefully."""
        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir()

        blue = [{"c": "Ahri", "r": "mid"}]
        red = [{"c": "Zed", "r": "mid"}]

        match_data = [
            {
                "match_id": "m1",
                "blue_team": json.dumps(blue),
                "red_team": json.dumps(red),
                "winner": "BLUE",
            }
        ]

        # Write JSON file so loading works
        (parsed_dir / "match.json").write_text(json.dumps(match_data))

        # Make ArtifactStats raise a validation error
        mock_artifact_stats.side_effect = ValueError("Invalid stats")

        result = build_tables()
        assert result is None

    @patch("app.ml.build_tables.settings")
    def test_build_tables_single_dict_json(self, mock_settings, tmp_path: Path):
        """Test loading a JSON file containing a single dict, not a list."""
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir(parents=True)

        match_data = {"match_id": "m1", "blue_team": "[]", "red_team": "[]", "winner": "BLUE"}
        (parsed_dir / "match.json").write_text(json.dumps(match_data))

        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"
        mock_settings.artifacts_path = tmp_path / "artifacts"

        # Result will be None because participants empty (blue_team is empty string list)
        assert build_tables() is None

    @patch("app.ml.build_tables.settings")
    def test_build_tables_malformed_json_content(self, mock_settings, tmp_path: Path):
        """Test JSON file that raises exception during load."""
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir(parents=True)

        (parsed_dir / "bad.json").write_text("{invalid")

        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"

        # Should return None because no valid data loaded if only bad file
        assert build_tables() is None

    @patch("app.ml.build_tables.settings")
    def test_build_tables_no_participants_extracted(self, mock_settings, tmp_path: Path):
        """Test when match data is valid JSON but malformed structure (key error)."""
        parsed_dir = tmp_path / "parsed"
        parsed_dir.mkdir(parents=True)

        # Missing blue_team key
        match_data = [{"match_id": "m1"}]
        (parsed_dir / "match.json").write_text(json.dumps(match_data))

        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"

        # Should hit malformed_count increment and return None (no participants)
        assert build_tables() is None

    @patch("app.ml.build_tables.settings")
    @patch("app.ml.build_tables.pd.DataFrame")
    def test_build_tables_dataframe_creation_error(
        self, mock_df_cls, mock_settings, tmp_path: Path
    ):
        """Test exception during DataFrame creation."""
        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"
        (tmp_path / "parsed").mkdir()
        (tmp_path / "parsed" / "m.json").write_text('{"id": 1}')

        mock_df_cls.side_effect = Exception("Pandas Error")

        assert build_tables() is None

    @patch("app.ml.build_tables.settings")
    def test_build_tables_no_json_files(self, mock_settings, tmp_path: Path):
        """Should handle case where parsed directory exists but has no JSON files."""
        mock_settings.data_root = tmp_path
        mock_settings.ingest.paths.parsed_dir = "parsed"
        (tmp_path / "parsed").mkdir()

        # Dir exists, but is empty (no .json files)
        result = build_tables()
        assert result is None
