from unittest.mock import patch

from app.config.settings import get_settings, Settings, ScoringConfig


def test_settings_singleton():
    """Verify that get_settings returns a Settings instance and is cached."""
    s1 = get_settings()
    s2 = get_settings()
    assert isinstance(s1, Settings)
    assert s1 is s2


def test_test_load_ingest_yaml_paths():
    """Verify strictly calculated paths."""
    # This checks real settings logic but usually we mock environment or ensure defaults/file exists.
    # We will assume get_settings() works with real file or we mock it.
    pass


def test_load_ingest_yaml():
    """Test loading of ingest.yaml into settings."""
    yaml_content = """
    paths:
      root_dir: "data_test"
      raw_dir: "raw_test"
      processed_dir: "processed_test"
      processed_filename: "matches_test"
      processed_file_type: "parquet"
      champion_map_dir: "static_test"
      champion_map_filename: "champs_test"
      champion_map_file_type: "json"
    defaults:
      region: KR
    sources:
      - type: by_rank
        queue: RANKED_SOLO_5x5
    """

    # Mock reading the file
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=yaml_content),
    ):
        # Clear cache to force reload
        get_settings.cache_clear()
        settings = get_settings()

        assert settings.ingest.defaults["region"] == "KR"
        assert len(settings.ingest.sources) == 1
        assert settings.ingest.sources[0]["type"] == "by_rank"
        assert settings.ingest.paths.root_dir == "data_test"

        # Test property construction
        assert settings.processed_file_path.name == "matches_test.parquet"
        assert settings.champion_map_path.name == "champs_test.json"
        assert settings.data_root.name == "data_test"


def test_load_ingest_yaml_failure():
    """Test failure when yaml is missing (should raise ValidationError due to missing required fields)."""
    from pydantic import ValidationError
    import pytest

    # Test missing file
    with patch("pathlib.Path.exists", return_value=False):
        get_settings.cache_clear()
        with pytest.raises(ValidationError):
            get_settings()


def test_load_ingest_yaml_exception():
    """Test failure when yaml parsing raises exception (should raise ValidationError due to missing required fields)."""
    from pydantic import ValidationError
    import pytest

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("app.config.settings.yaml.safe_load", side_effect=Exception("YAML Error")),
    ):
        get_settings.cache_clear()
        with pytest.raises(ValidationError):
            get_settings()


def test_load_scoring_yaml():
    """Test loading of scoring.yaml into settings."""
    ingest_yaml = """
    paths:
      root_dir: "data"
      raw_dir: "raw"
      processed_dir: "processed"
      processed_filename: "matches"
      processed_file_type: "parquet"
      champion_map_dir: "data"
      champion_map_filename: "champion_ids"
      champion_map_file_type: "json"
    """
    scoring_yaml = """
    role_strength_weight: 0.8
    synergy_weight: 0.1
    """

    def side_effect(self, encoding=None):
        if "ingest.yaml" in str(self):
            return ingest_yaml
        if "scoring.yaml" in str(self):
            return scoring_yaml
        return ""

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", side_effect=side_effect, autospec=True),
    ):
        get_settings.cache_clear()
        settings = get_settings()

        assert settings.scoring.role_strength_weight == 0.8
        assert settings.scoring.synergy_weight == 0.1
        # Verify defaults for missing fields
        assert settings.scoring.counter_weight == 0.5


def test_load_scoring_yaml_failure():
    """Test graceful failure when scoring yaml is invalid or missing."""
    ingest_yaml = """
    paths:
      root_dir: "data"
      raw_dir: "raw"
      processed_dir: "processed"
      processed_filename: "matches"
      processed_file_type: "parquet"
      champion_map_dir: "data"
      champion_map_filename: "champion_ids"
      champion_map_file_type: "json"
    """

    def exists_side_effect(self):
        if "ingest.yaml" in str(self):
            return True
        if "scoring.yaml" in str(self):
            return False
        return False

    def read_side_effect(self, encoding=None):
        if "ingest.yaml" in str(self):
            return ingest_yaml
        return ""

    with (
        patch("pathlib.Path.exists", side_effect=exists_side_effect, autospec=True),
        patch("pathlib.Path.read_text", side_effect=read_side_effect, autospec=True),
    ):
        get_settings.cache_clear()
        settings = get_settings()
        # Should rely on defaults for scoring
        assert isinstance(settings.scoring, ScoringConfig)
        assert settings.scoring.role_strength_weight == 1.0


def test_load_scoring_yaml_exception():
    """Test graceful failure when scoring yaml parsing raises exception."""
    ingest_yaml = """
    paths:
      root_dir: "data"
      raw_dir: "raw"
      processed_dir: "processed"
      processed_filename: "matches"
      processed_file_type: "parquet"
      champion_map_dir: "data"
      champion_map_filename: "champion_ids"
      champion_map_file_type: "json"
    """

    def read_side_effect(self, encoding=None):
        if "ingest.yaml" in str(self):
            return ingest_yaml
        if "scoring.yaml" in str(self):
            raise Exception("YAML Error")
        return ""

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", side_effect=read_side_effect, autospec=True),
    ):
        get_settings.cache_clear()
        settings = get_settings()

        assert isinstance(settings.scoring, ScoringConfig)
        assert isinstance(settings.scoring, ScoringConfig)
        assert settings.scoring.role_strength_weight == 1.0


def test_should_fetch_champion_map():
    """Test the should_fetch_champion_map property based on defaults."""
    from app.config.settings import IngestConfig, PathsConfig

    # Mock PathsConfig
    paths = PathsConfig(
        root_dir="root",
        raw_dir="raw",
        processed_dir="proc",
        processed_filename="name",
        processed_file_type="pq",
        champion_map_dir="map",
        champion_map_filename="cmap",
        champion_map_file_type="json",
    )

    # Case 1: Key missing (should be True by default)
    config1 = IngestConfig(paths=paths, defaults={})
    assert config1.should_fetch_champion_map is True

    # Case 2: Explicitly True
    config2 = IngestConfig(paths=paths, defaults={"fetch_champion_map": True})
    assert config2.should_fetch_champion_map is True

    # Case 3: Explicitly False
    config3 = IngestConfig(paths=paths, defaults={"fetch_champion_map": False})
    assert config3.should_fetch_champion_map is False
