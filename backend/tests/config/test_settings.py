from unittest.mock import patch

from app.config.settings import get_settings, Settings, IngestConfig


def test_settings_singleton():
    """Verify that get_settings returns a Settings instance and is cached."""
    s1 = get_settings()
    s2 = get_settings()
    assert isinstance(s1, Settings)
    assert s1 is s2


def test_settings_paths():
    """Verify strictly calculated paths."""
    settings = get_settings()

    assert settings.backend_root.name == "backend"
    assert settings.data_root.name == "data"
    assert settings.champion_map_path.name == "champion_ids.json"


def test_load_ingest_yaml():
    """Test loading of ingest.yaml into settings."""
    yaml_content = """
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


def test_load_ingest_yaml_failure():
    """Test graceful failure when yaml is invalid or missing."""
    # Test missing file
    with patch("pathlib.Path.exists", return_value=False):
        get_settings.cache_clear()
        settings = get_settings()
        # Should rely on defaults
        assert isinstance(settings.ingest, IngestConfig)
        assert settings.ingest.sources == []


def test_load_ingest_yaml_exception():
    """Test graceful failure when yaml parsing raises exception."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("app.config.settings.yaml.safe_load", side_effect=Exception("YAML Error")),
    ):
        get_settings.cache_clear()
        settings = get_settings()

        assert isinstance(settings.ingest, IngestConfig)
        assert settings.ingest.sources == []
