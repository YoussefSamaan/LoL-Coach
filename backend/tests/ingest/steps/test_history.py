import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from app.ingest.steps.history import ScanHistoryStep
from app.ingest.pipeline import PipelineContext


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock pipeline context."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    context.state["players"] = [
        {"puuid": "puuid1", "tier": "CHALLENGER", "division": "I"},
        {"puuid": "puuid2", "tier": "CHALLENGER", "division": "I"},
    ]
    return context


@pytest.fixture
def mock_settings(tmp_path):
    """Mock settings."""
    with patch("app.ingest.steps.history.settings") as mock:
        mock.ingest.defaults = {
            "region": "NA",
            "matches_per_player": 2,
        }
        mock.data_root = tmp_path
        mock.ingest.paths.manifest_dir = "manifests"
        yield mock


@pytest.fixture
def mock_crawler():
    """Mock RiotCrawler."""
    with patch("app.ingest.steps.history.RiotCrawler") as MockCrawler:
        crawler_instance = Mock()
        crawler_instance.scan_match_history.return_value = [
            "NA1_match1",
            "NA1_match2",
        ]
        MockCrawler.return_value = crawler_instance
        yield crawler_instance


@pytest.fixture
def mock_get_date_str():
    """Mock get_date_str to return consistent date."""
    with patch("app.ingest.steps.history.get_date_str") as mock:
        mock.return_value = "2024-01-15"
        yield mock


def test_scan_history_step_name():
    """Test that the step has the correct name."""
    step = ScanHistoryStep()
    assert step.name == "Scan Histories"


def test_scan_history_step_no_players(tmp_path, mock_settings):
    """Test when no players are in context."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    step = ScanHistoryStep()
    step.run(context)

    # Should return early without doing anything
    assert "match_ids" not in context.state


def test_scan_history_step_success(mock_context, mock_settings, mock_crawler, mock_get_date_str):
    """Test successful history scan with new matches."""
    step = ScanHistoryStep()
    step.run(mock_context)

    # Verify crawler was called for each player
    assert mock_crawler.scan_match_history.call_count == 2
    mock_crawler.scan_match_history.assert_any_call("NA", ["puuid1"], 2, start_time=0)
    mock_crawler.scan_match_history.assert_any_call("NA", ["puuid2"], 2, start_time=0)

    # Verify match_ids were added
    assert "match_ids" in mock_context.state
    match_ids = mock_context.state["match_ids"]
    assert len(match_ids) == 2  # Both players return same matches, deduplicated
    assert "NA1_match1" in match_ids
    assert "NA1_match2" in match_ids

    # Verify match_rank_map was created
    assert "match_rank_map" in mock_context.state
    match_rank_map = mock_context.state["match_rank_map"]
    assert match_rank_map["NA1_match1"] == {
        "tier": "CHALLENGER",
        "division": "I",
        "region": "NA",
    }

    # Verify manifest file was created
    manifest_file = (
        mock_settings.data_root / "manifests" / "NA" / "CHALLENGER" / "I" / "2024-01-15.txt"
    )
    assert manifest_file.exists()
    content = manifest_file.read_text().splitlines()
    assert len(content) == 2  # 2 unique matches after deduplication


def test_scan_history_step_with_existing_manifest(
    mock_context, mock_settings, mock_crawler, mock_get_date_str, tmp_path
):
    """Test that existing matches in manifest are skipped."""
    # Create existing manifest with one match
    manifest_dir = tmp_path / "manifests" / "NA" / "CHALLENGER" / "I"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    existing_manifest = manifest_dir / "2024-01-10.txt"
    existing_manifest.write_text("NA1_match1\n")

    step = ScanHistoryStep()
    step.run(mock_context)

    match_ids = mock_context.state["match_ids"]
    assert len(match_ids) == 1


def test_scan_history_step_with_min_match_time(
    mock_context, mock_settings, mock_crawler, mock_get_date_str
):
    """Test that min_match_time is passed to crawler."""
    mock_context.state["min_match_time"] = 1704067200

    step = ScanHistoryStep()
    step.run(mock_context)

    # Verify min_time was passed
    mock_crawler.scan_match_history.assert_any_call("NA", ["puuid1"], 2, start_time=1704067200)


def test_scan_history_step_crawler_exception(
    mock_context, mock_settings, mock_crawler, mock_get_date_str
):
    """Test handling of crawler exceptions."""
    mock_crawler.scan_match_history.side_effect = [
        Exception("API Error"),
        ["NA1_match3"],
    ]

    step = ScanHistoryStep()
    step.run(mock_context)

    # Should continue processing other players despite exception
    match_ids = mock_context.state["match_ids"]
    assert len(match_ids) == 1
    assert "NA1_match3" in match_ids


def test_scan_history_step_manifest_read_exception(
    mock_context, mock_settings, mock_crawler, mock_get_date_str, tmp_path
):
    """Test handling of manifest read exceptions."""
    # Create a manifest file that will cause read error
    manifest_dir = tmp_path / "manifests" / "NA" / "CHALLENGER" / "I"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    bad_manifest = manifest_dir / "corrupt.txt"
    bad_manifest.write_bytes(b"\xff\xfe")  # Invalid UTF-8

    # Mock glob to return the corrupt file
    with patch.object(Path, "glob") as mock_glob:
        mock_glob.return_value = [bad_manifest]

        step = ScanHistoryStep()
        step.run(mock_context)

        # Should still process matches despite manifest read error
        assert "match_ids" in mock_context.state


def test_scan_history_step_deduplication_within_run(mock_context, mock_settings, mock_get_date_str):
    """Test that duplicates within the same run are handled."""
    with patch("app.ingest.steps.history.RiotCrawler") as MockCrawler:
        crawler_instance = Mock()
        # Both players return the same match
        crawler_instance.scan_match_history.return_value = ["NA1_same_match"]
        MockCrawler.return_value = crawler_instance

        step = ScanHistoryStep()
        step.run(mock_context)

        # Should only have 1 match despite 2 players returning it
        match_ids = mock_context.state["match_ids"]
        assert len(match_ids) == 1
        assert "NA1_same_match" in match_ids


def test_scan_history_step_multiple_tiers(mock_settings, mock_get_date_str, tmp_path):
    """Test handling players from different tiers."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    context.state["players"] = [
        {"puuid": "puuid1", "tier": "CHALLENGER", "division": "I"},
        {"puuid": "puuid2", "tier": "GRANDMASTER", "division": "I"},
    ]

    with patch("app.ingest.steps.history.RiotCrawler") as MockCrawler:
        crawler_instance = Mock()
        crawler_instance.scan_match_history.side_effect = [
            ["NA1_match1"],
            ["NA1_match2"],
        ]
        MockCrawler.return_value = crawler_instance

        step = ScanHistoryStep()
        step.run(context)

        # Should create separate manifest files for each tier
        challenger_manifest = tmp_path / "manifests" / "NA" / "CHALLENGER" / "I" / "2024-01-15.txt"
        grandmaster_manifest = (
            tmp_path / "manifests" / "NA" / "GRANDMASTER" / "I" / "2024-01-15.txt"
        )

        assert challenger_manifest.exists()
        assert grandmaster_manifest.exists()

        # Verify match_rank_map has correct tiers
        match_rank_map = context.state["match_rank_map"]
        assert match_rank_map["NA1_match1"]["tier"] == "CHALLENGER"
        assert match_rank_map["NA1_match2"]["tier"] == "GRANDMASTER"


def test_scan_history_step_manifest_caching(
    mock_context, mock_settings, mock_crawler, mock_get_date_str, tmp_path
):
    """Test that manifest is cached in context to avoid re-reading."""
    # Create existing manifest
    manifest_dir = tmp_path / "manifests" / "NA" / "CHALLENGER" / "I"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    existing_manifest = manifest_dir / "2024-01-10.txt"
    existing_manifest.write_text("NA1_old_match\n")

    step = ScanHistoryStep()
    step.run(mock_context)

    # Verify manifest was cached in context
    assert "manifest_NA/CHALLENGER/I" in mock_context.state
    cached_manifest = mock_context.state["manifest_NA/CHALLENGER/I"]
    assert "NA1_old_match" in cached_manifest


def test_scan_history_step_empty_history(mock_context, mock_settings, mock_get_date_str):
    """Test when crawler returns no matches."""
    with patch("app.ingest.steps.history.RiotCrawler") as MockCrawler:
        crawler_instance = Mock()
        crawler_instance.scan_match_history.return_value = []
        MockCrawler.return_value = crawler_instance

        step = ScanHistoryStep()
        step.run(mock_context)

        # Should have empty match_ids
        assert mock_context.state["match_ids"] == set()
