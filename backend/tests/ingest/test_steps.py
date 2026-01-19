import pytest
from unittest.mock import patch
from pathlib import Path

from app.ingest.steps import (
    FetchStaticDataStep,
    ScanLadderStep,
    ScanHistoryStep,
    DownloadContentStep,
    ProcessDataStep,
    CleanupStep,
)
from app.ingest.pipeline import PipelineContext


@pytest.fixture
def mock_context(tmp_path):
    return PipelineContext(run_id="test", base_dir=tmp_path)


@patch("app.ingest.steps.settings")
@patch("app.ingest.steps.DataDragonClient")
def test_fetch_static_data_enabled(MockClient, mock_settings, mock_context):
    step = FetchStaticDataStep()

    # Configure settings
    mock_settings.ingest.should_fetch_champion_map = True
    # Keep it a mock, just set attributes
    mock_settings.champion_map_path.name = "map.json"
    mock_settings.champion_map_path.exists.return_value = False

    step.run(mock_context)

    # MockClient() create instance -> instance.save_champion_map()
    MockClient.return_value.save_champion_map.assert_called_once()
    assert mock_context.state["champion_map_path"] == mock_settings.champion_map_path


@patch("app.ingest.steps.settings")
@patch("app.ingest.steps.DataDragonClient")
def test_fetch_static_data_disabled(MockClient, mock_settings, mock_context):
    step = FetchStaticDataStep()

    mock_settings.ingest.should_fetch_champion_map = False
    mock_settings.champion_map_path.name = "map.json"
    mock_settings.champion_map_path.exists.return_value = False

    step.run(mock_context)

    MockClient.return_value.save_champion_map.assert_not_called()


@patch("app.ingest.steps.settings")
@patch("app.ingest.steps.RiotCrawler")
def test_scan_ladder(MockCrawler, mock_settings, mock_context):
    step = ScanLadderStep()

    # Prepare source config with real strings for Enums
    start_src = [
        {"type": "ladder", "region": "NA", "queue": "RANKED_SOLO_5x5", "tier": "CHALLENGER"}
    ]
    mock_settings.ingest.sources = start_src

    # Mock defaults to be a real dict so .get works
    mock_settings.ingest.defaults = {"region": "NA"}

    MockCrawler.return_value.fetch_ladder_puuids.return_value = ["p1", "p2"]

    step.run(mock_context)

    assert set(mock_context.state["puuids"]) == {"p1", "p2"}
    MockCrawler.return_value.fetch_ladder_puuids.assert_called()


@patch("app.ingest.steps.settings")
@patch("app.ingest.steps.RiotCrawler")
def test_scan_history(MockCrawler, mock_settings, mock_context):
    step = ScanHistoryStep()
    mock_context.state["puuids"] = ["p1"]

    # Ensure defaults.get returns a valid string for Region enum
    mock_settings.ingest.defaults = {"region": "NA", "matches_per_player": 2}

    MockCrawler.return_value.scan_match_history.return_value = {"m1"}

    step.run(mock_context)

    assert mock_context.state["match_ids"] == {"m1"}
    MockCrawler.return_value.scan_match_history.assert_called()


@patch("app.ingest.steps.settings")
@patch("app.ingest.steps.RiotCrawler")
def test_download_content(MockCrawler, mock_settings, mock_context):
    step = DownloadContentStep()
    mock_context.state["match_ids"] = {"m1"}
    mock_settings.ingest.paths.raw_dir = "raw"

    step.run(mock_context)

    assert "raw_dir" in mock_context.state
    MockCrawler.return_value.download_matches.assert_called()


@patch("app.ingest.steps.settings")
@patch("app.ingest.steps.MatchProcessor")
def test_process_data(MockProcessor, mock_settings, mock_context):
    step = ProcessDataStep()
    mock_context.state["raw_dir"] = Path("/tmp/raw")

    mock_settings.ingest.paths.processed_file_type = "parquet"
    mock_settings.processed_file_path = Path("/tmp/out.parquet")
    mock_settings.champion_map_path = Path("/tmp/map.json")

    step.run(mock_context)

    MockProcessor.return_value.process_dir.assert_called()
    assert mock_context.state["processed_file"] == mock_settings.processed_file_path


def test_cleanup_step(mock_context):
    target = mock_context.base_dir / "temp_dir"
    target.mkdir()

    mock_context.state["target"] = target

    step = CleanupStep("target")
    step.run(mock_context)

    assert not target.exists()


def test_scan_history_no_puuids(mock_context):
    step = ScanHistoryStep()
    mock_context.state["puuids"] = []

    with patch("app.ingest.steps.RiotCrawler") as MockCrawler:
        step.run(mock_context)
        MockCrawler.return_value.scan_match_history.assert_not_called()


def test_download_content_no_ids(mock_context):
    step = DownloadContentStep()
    mock_context.state["match_ids"] = set()

    with patch("app.ingest.steps.RiotCrawler") as MockCrawler:
        step.run(mock_context)
        MockCrawler.return_value.download_matches.assert_not_called()


def test_process_no_raw_dir(mock_context):
    step = ProcessDataStep()
    # No raw_dir in state
    with patch("app.ingest.steps.MatchProcessor") as MockProc:
        step.run(mock_context)
        MockProc.return_value.process_dir.assert_not_called()


def test_cleanup_file(mock_context):
    target = mock_context.base_dir / "file.txt"
    target.write_text("ok")

    mock_context.state["target"] = target
    step = CleanupStep("target")
    step.run(mock_context)

    assert not target.exists()


def test_get_date_str():
    from app.ingest.steps import get_date_str

    assert len(get_date_str()) == 10  # YYYY-MM-DD
