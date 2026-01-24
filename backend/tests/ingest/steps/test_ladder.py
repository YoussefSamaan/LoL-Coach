import pytest
from unittest.mock import Mock, patch
from app.ingest.steps.ladder import ScanLadderStep
from app.ingest.pipeline import PipelineContext
from app.domain.enums import Region, QueueType, Tier, Division


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock pipeline context."""
    return PipelineContext(run_id="test_run", base_dir=tmp_path)


@pytest.fixture
def mock_settings():
    """Mock settings with ladder sources."""
    with patch("app.ingest.steps.ladder.settings") as mock:
        mock.ingest.defaults = {
            "region": "NA",
            "queue": "RANKED_SOLO_5x5",
        }
        mock.ingest.sources = [
            {
                "type": "ladder",
                "region": "NA",
                "queue": "RANKED_SOLO_5x5",
                "tier": "CHALLENGER",
                "division": "I",
                "count": 5,
            }
        ]
        yield mock


@pytest.fixture
def mock_crawler():
    """Mock RiotCrawler."""
    with patch("app.ingest.steps.ladder.RiotCrawler") as MockCrawler:
        crawler_instance = Mock()
        crawler_instance.fetch_ladder_puuids.return_value = [
            "puuid1",
            "puuid2",
            "puuid3",
        ]
        MockCrawler.return_value = crawler_instance
        yield crawler_instance


def test_scan_ladder_step_name():
    """Test that the step has the correct name."""
    step = ScanLadderStep()
    assert step.name == "Scan Ladder"


def test_scan_ladder_step_success(mock_context, mock_settings, mock_crawler):
    """Test successful ladder scan."""
    step = ScanLadderStep()
    step.run(mock_context)

    # Verify crawler was called correctly
    mock_crawler.fetch_ladder_puuids.assert_called_once_with(
        Region.NA,
        QueueType.RANKED_SOLO_5x5,
        Tier.CHALLENGER,
        Division.I,
        5,
    )

    # Verify players were added to context
    assert "players" in mock_context.state
    players = mock_context.state["players"]
    assert len(players) == 3
    assert players[0] == {"puuid": "puuid1", "tier": "CHALLENGER", "division": "I"}
    assert players[1] == {"puuid": "puuid2", "tier": "CHALLENGER", "division": "I"}
    assert players[2] == {"puuid": "puuid3", "tier": "CHALLENGER", "division": "I"}


def test_scan_ladder_step_multiple_sources(mock_context, mock_crawler):
    """Test scanning multiple ladder sources."""
    with patch("app.ingest.steps.ladder.settings") as mock_settings:
        mock_settings.ingest.defaults = {"region": "NA", "queue": "RANKED_SOLO_5x5"}
        mock_settings.ingest.sources = [
            {
                "type": "ladder",
                "region": "NA",
                "tier": "CHALLENGER",
                "division": "I",
                "count": 2,
            },
            {
                "type": "ladder",
                "region": "EUW",
                "tier": "GRANDMASTER",
                "division": "I",
                "count": 3,
            },
        ]

        mock_crawler.fetch_ladder_puuids.side_effect = [
            ["puuid1", "puuid2"],
            ["puuid3", "puuid4", "puuid5"],
        ]

        step = ScanLadderStep()
        step.run(mock_context)

        # Verify both sources were processed
        assert mock_crawler.fetch_ladder_puuids.call_count == 2
        players = mock_context.state["players"]
        assert len(players) == 5


def test_scan_ladder_step_with_defaults(mock_context, mock_crawler):
    """Test that defaults are used when source doesn't specify values."""
    with patch("app.ingest.steps.ladder.settings") as mock_settings:
        mock_settings.ingest.defaults = {
            "region": "EUW",
            "queue": "RANKED_SOLO_5x5",
        }
        mock_settings.ingest.sources = [
            {
                "type": "ladder",
                "tier": "MASTER",
                "division": "I",
                "count": 1,
            }
        ]

        mock_crawler.fetch_ladder_puuids.return_value = ["puuid_test"]

        step = ScanLadderStep()
        step.run(mock_context)

        # Verify defaults were used
        mock_crawler.fetch_ladder_puuids.assert_called_once_with(
            Region.EUW,
            QueueType.RANKED_SOLO_5x5,
            Tier.MASTER,
            Division.I,
            1,
        )


def test_scan_ladder_step_non_ladder_sources(mock_context, mock_crawler):
    """Test that non-ladder sources are skipped."""
    with patch("app.ingest.steps.ladder.settings") as mock_settings:
        mock_settings.ingest.defaults = {"region": "NA", "queue": "RANKED_SOLO_5x5"}
        mock_settings.ingest.sources = [
            {"type": "other_type", "count": 10},
            {
                "type": "ladder",
                "tier": "CHALLENGER",
                "division": "I",
                "count": 1,
            },
        ]

        mock_crawler.fetch_ladder_puuids.return_value = ["puuid1"]

        step = ScanLadderStep()
        step.run(mock_context)

        # Should only be called once (for ladder source)
        assert mock_crawler.fetch_ladder_puuids.call_count == 1


def test_scan_ladder_step_empty_sources(mock_context, mock_crawler):
    """Test with no ladder sources."""
    with patch("app.ingest.steps.ladder.settings") as mock_settings:
        mock_settings.ingest.defaults = {"region": "NA"}
        mock_settings.ingest.sources = []

        step = ScanLadderStep()
        step.run(mock_context)

        # Crawler should not be called
        mock_crawler.fetch_ladder_puuids.assert_not_called()
        # Players list should still be created (empty)
        assert mock_context.state["players"] == []


def test_scan_ladder_step_no_puuids_returned(mock_context, mock_settings, mock_crawler):
    """Test when crawler returns empty list."""
    mock_crawler.fetch_ladder_puuids.return_value = []

    step = ScanLadderStep()
    step.run(mock_context)

    assert mock_context.state["players"] == []
