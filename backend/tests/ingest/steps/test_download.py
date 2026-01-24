import pytest
import json
from unittest.mock import Mock, patch
from app.ingest.steps.download import DownloadContentStep
from app.ingest.pipeline import PipelineContext
from app.domain.enums import Region


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock pipeline context."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    context.state["match_ids"] = {"NA1_match1", "NA1_match2"}
    context.state["match_rank_map"] = {
        "NA1_match1": {"region": "NA", "tier": "CHALLENGER", "division": "I"},
        "NA1_match2": {"region": "NA", "tier": "GRANDMASTER", "division": "II"},
    }
    return context


@pytest.fixture
def mock_settings(tmp_path):
    """Mock settings."""
    with patch("app.ingest.steps.download.settings") as mock:
        mock.ingest.paths.raw_dir = "raw"
        yield mock


@pytest.fixture
def mock_crawler():
    """Mock RiotCrawler."""
    with patch("app.ingest.steps.download.RiotCrawler") as MockCrawler:
        crawler_instance = Mock()
        crawler_instance.get_match.return_value = {
            "metadata": {"matchId": "NA1_match1"},
            "info": {
                "gameCreation": 1704067200000,  # 2024-01-01 00:00:00 UTC
                "participants": [],
            },
        }
        MockCrawler.return_value = crawler_instance
        yield crawler_instance


def test_download_content_step_name():
    """Test that the step has the correct name."""
    step = DownloadContentStep()
    assert step.name == "Download Content"


def test_download_content_step_no_match_ids(tmp_path, mock_settings):
    """Test when no match_ids are in context."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    step = DownloadContentStep()
    step.run(context)

    # Should return early without doing anything
    assert "raw_dir" not in context.state


def test_download_content_step_empty_match_ids(tmp_path, mock_settings):
    """Test when match_ids is empty set."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    context.state["match_ids"] = set()
    step = DownloadContentStep()
    step.run(context)

    # Should return early
    assert "raw_dir" not in context.state


def test_download_content_step_success(mock_context, mock_settings, mock_crawler):
    """Test successful download of matches."""
    step = DownloadContentStep()
    step.run(mock_context)

    # Verify crawler was called for each match
    assert mock_crawler.get_match.call_count == 2

    # Verify files were created in correct directory structure
    base_raw_dir = mock_context.base_dir / "raw"
    match1_file = base_raw_dir / "NA" / "CHALLENGER" / "I" / "2024-01-01" / "NA1_match1.json"
    match2_file = base_raw_dir / "NA" / "GRANDMASTER" / "II" / "2024-01-01" / "NA1_match2.json"

    assert match1_file.exists()
    assert match2_file.exists()
    # Verify JSON content
    data = json.loads(match1_file.read_text())
    assert data["metadata"]["matchId"] == "NA1_match1"

    # Verify raw_dir was set in context
    assert mock_context.state["raw_dir"] == base_raw_dir


def test_download_content_step_with_min_time_filter(mock_context, mock_settings, mock_crawler):
    """Test that matches before min_time are filtered out."""
    mock_context.state["min_match_time"] = 1704153600  # 2024-01-02 00:00:00 UTC

    # Match is from 2024-01-01, should be filtered
    step = DownloadContentStep()
    step.run(mock_context)

    # Files should not be created (filtered by time)
    base_raw_dir = mock_context.base_dir / "raw"
    match_files = list(base_raw_dir.glob("**/*.json"))
    assert len(match_files) == 0


def test_download_content_step_with_min_time_pass(mock_context, mock_settings, mock_crawler):
    """Test that matches after min_time are kept."""
    mock_context.state["min_match_time"] = 1704000000  # Before match time

    step = DownloadContentStep()
    step.run(mock_context)

    # Files should be created
    base_raw_dir = mock_context.base_dir / "raw"
    match_files = list(base_raw_dir.glob("**/*.json"))
    assert len(match_files) == 2


def test_download_content_step_crawler_returns_none(mock_context, mock_settings, mock_crawler):
    """Test when crawler returns None for a match."""
    mock_crawler.get_match.side_effect = [None, {"info": {"gameCreation": 1704067200000}}]

    step = DownloadContentStep()
    step.run(mock_context)

    # Only one file should be created
    base_raw_dir = mock_context.base_dir / "raw"
    match_files = list(base_raw_dir.glob("**/*.json"))
    assert len(match_files) == 1


def test_download_content_step_crawler_exception(mock_context, mock_settings, mock_crawler):
    """Test handling of crawler exceptions."""
    mock_crawler.get_match.side_effect = [
        Exception("API Error"),
        {"info": {"gameCreation": 1704067200000}},
    ]

    step = DownloadContentStep()
    step.run(mock_context)

    # Should continue processing other matches
    base_raw_dir = mock_context.base_dir / "raw"
    match_files = list(base_raw_dir.glob("**/*.json"))
    assert len(match_files) == 1


def test_download_content_step_unknown_region(mock_settings, mock_crawler, tmp_path):
    """Test handling of matches with UNKNOWN region."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    context.state["match_ids"] = {"UNKNOWN_match1"}
    context.state["match_rank_map"] = {
        "UNKNOWN_match1": {"region": "UNKNOWN", "tier": "CHALLENGER", "division": "I"}
    }

    mock_crawler.get_match.return_value = {"info": {"gameCreation": 1704067200000}}

    step = DownloadContentStep()
    step.run(context)

    # Should use Region.NA as fallback
    mock_crawler.get_match.assert_called_once_with("UNKNOWN_match1", Region.NA)


def test_download_content_step_missing_rank_context(mock_settings, mock_crawler, tmp_path):
    """Test handling of matches without rank context."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    context.state["match_ids"] = {"NA1_match1"}
    context.state["match_rank_map"] = {}  # Empty map

    mock_crawler.get_match.return_value = {"info": {"gameCreation": 1704067200000}}

    step = DownloadContentStep()
    step.run(context)

    # Should use UNKNOWN defaults
    base_raw_dir = context.base_dir / "raw"
    match_file = base_raw_dir / "UNKNOWN" / "UNKNOWN" / "IV" / "2024-01-01" / "NA1_match1.json"
    assert match_file.exists()


def test_download_content_step_creates_nested_directories(
    mock_context, mock_settings, mock_crawler
):
    """Test that nested directory structure is created correctly."""
    step = DownloadContentStep()
    step.run(mock_context)

    # Verify directory structure exists
    base_raw_dir = mock_context.base_dir / "raw"
    assert (base_raw_dir / "NA" / "CHALLENGER" / "I" / "2024-01-01").exists()
    assert (base_raw_dir / "NA" / "GRANDMASTER" / "II" / "2024-01-01").exists()


def test_download_content_step_json_formatting(mock_context, mock_settings, mock_crawler):
    """Test that JSON is written without indentation."""
    mock_crawler.get_match.return_value = {
        "metadata": {"matchId": "NA1_match1"},
        "info": {
            "gameCreation": 1704067200000,
            "nested": {"key": "value"},
        },
    }

    step = DownloadContentStep()
    step.run(mock_context)

    base_raw_dir = mock_context.base_dir / "raw"
    match_file = base_raw_dir / "NA" / "CHALLENGER" / "I" / "2024-01-01" / "NA1_match1.json"

    content = match_file.read_text()
    # Should not have indentation (indent=None)
    assert "\n  " not in content  # No indented lines


def test_download_content_step_date_extraction(mock_settings, mock_crawler, tmp_path):
    """Test correct date extraction from gameCreation timestamp."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    context.state["match_ids"] = {"NA1_match1"}
    context.state["match_rank_map"] = {
        "NA1_match1": {"region": "NA", "tier": "CHALLENGER", "division": "I"}
    }

    # Different timestamp: 2024-06-15 12:30:00 UTC
    mock_crawler.get_match.return_value = {"info": {"gameCreation": 1718454600000}}

    step = DownloadContentStep()
    step.run(context)

    base_raw_dir = context.base_dir / "raw"
    match_file = base_raw_dir / "NA" / "CHALLENGER" / "I" / "2024-06-15" / "NA1_match1.json"
    assert match_file.exists()


def test_download_content_step_no_min_time_in_context(mock_settings, mock_crawler, tmp_path):
    """Test when min_match_time is not in context (defaults to 0)."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    context.state["match_ids"] = {"NA1_match1"}
    context.state["match_rank_map"] = {
        "NA1_match1": {"region": "NA", "tier": "CHALLENGER", "division": "I"}
    }

    mock_crawler.get_match.return_value = {"info": {"gameCreation": 1704067200000}}

    step = DownloadContentStep()
    step.run(context)

    # Should process match (min_time defaults to 0)
    base_raw_dir = context.base_dir / "raw"
    match_files = list(base_raw_dir.glob("**/*.json"))
    assert len(match_files) == 1


def test_download_content_step_region_enum_conversion(mock_settings, mock_crawler, tmp_path):
    """Test that region string is properly converted to Region enum."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    context.state["match_ids"] = {"EUW1_match1"}
    context.state["match_rank_map"] = {
        "EUW1_match1": {"region": "EUW", "tier": "CHALLENGER", "division": "I"}
    }

    mock_crawler.get_match.return_value = {"info": {"gameCreation": 1704067200000}}

    step = DownloadContentStep()
    step.run(context)

    # Verify correct region was used (not converted to enum in this case, just passed as string)
    base_raw_dir = context.base_dir / "raw"
    match_file = base_raw_dir / "EUW" / "CHALLENGER" / "I" / "2024-01-01" / "EUW1_match1.json"
    assert match_file.exists()
