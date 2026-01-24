import pytest
import json
import pandas as pd
from unittest.mock import Mock, patch
from pathlib import Path
from app.ingest.steps.aggregate import AggregateStatsStep
from app.ingest.pipeline import PipelineContext


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock pipeline context."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()
    context.state["parsed_dir"] = parsed_dir
    return context


@pytest.fixture
def mock_settings(tmp_path):
    """Mock settings."""
    with patch("app.ingest.steps.aggregate.settings") as mock:
        mock.parsed_root = tmp_path / "parsed"
        mock.aggregates_root = tmp_path / "aggregates"
        yield mock


@pytest.fixture
def sample_parsed_data():
    """Create sample parsed match data."""
    return [
        {
            "match_id": "NA1_1",
            "region": "NA",
            "tier": "CHALLENGER",
            "division": "I",
            "day": "2024-01-01",
            "blue_team": json.dumps([
                {"champion": "Annie", "role": "MIDDLE"},
                {"champion": "Olaf", "role": "JUNGLE"},
            ]),
            "red_team": json.dumps([
                {"champion": "Darius", "role": "TOP"},
                {"champion": "Jinx", "role": "BOTTOM"},
            ]),
            "winner": "blue",
        }
    ]


@pytest.fixture
def mock_compute_aggregates():
    """Mock compute_aggregates function."""
    with patch("app.ingest.steps.aggregate.compute_aggregates") as mock:
        mock.return_value = {
            "Annie": {
                "wins": 1,
                "games": 1,
                "synergy": {},
                "counter": {},
            }
        }
        yield mock


def test_aggregate_stats_step_name():
    """Test that the step has the correct name."""
    step = AggregateStatsStep()
    assert step.name == "Aggregate Stats"


def test_aggregate_stats_step_no_parsed_dir(tmp_path, mock_settings):
    """Test when no parsed_dir is in context and default doesn't exist."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    
    step = AggregateStatsStep()
    step.run(context)

    # Should handle gracefully (no files to process)


def test_aggregate_stats_step_success(
    mock_context, mock_settings, sample_parsed_data, mock_compute_aggregates
):
    """Test successful aggregation of stats."""
    # Create parsed data file
    parsed_file = mock_context.state["parsed_dir"] / "NA" / "CHALLENGER" / "I" / "2024-01-01.json"
    parsed_file.parent.mkdir(parents=True, exist_ok=True)
    parsed_file.write_text(json.dumps(sample_parsed_data))

    step = AggregateStatsStep()
    step.run(mock_context)

    # Verify compute_aggregates was called
    mock_compute_aggregates.assert_called_once()

    # Verify output file was created
    output_file = mock_settings.aggregates_root / "NA" / "CHALLENGER" / "I" / "2024-01-01.json"
    assert output_file.exists()

    # Verify output content
    output_data = json.loads(output_file.read_text())
    assert output_data["date"] == "2024-01-01"
    assert output_data["region"] == "NA"
    assert output_data["tier"] == "CHALLENGER"
    assert output_data["division"] == "I"
    assert output_data["metrics"] == ["wins", "games"]
    assert "stats" in output_data


def test_aggregate_stats_step_no_files(mock_context, mock_settings):
    """Test when no parsed files exist."""
    step = AggregateStatsStep()
    step.run(mock_context)

    # Should log warning and return without error


def test_aggregate_stats_step_invalid_json_file(mock_context, mock_settings):
    """Test handling of invalid JSON files."""
    # Create invalid JSON file
    bad_file = mock_context.state["parsed_dir"] / "bad.json"
    bad_file.write_text("not valid json{")

    step = AggregateStatsStep()
    step.run(mock_context)

    # Should log warning and continue


def test_aggregate_stats_step_empty_file_list(mock_context, mock_settings):
    """Test when parsed data list is empty after loading."""
    # Create file with empty list
    empty_file = mock_context.state["parsed_dir"] / "empty.json"
    empty_file.write_text("[]")

    step = AggregateStatsStep()
    step.run(mock_context)

    # Should return early without creating aggregates


def test_aggregate_stats_step_multiple_files(
    mock_context, mock_settings, sample_parsed_data, mock_compute_aggregates
):
    """Test aggregation with multiple parsed files."""
    # Create multiple files
    for i in range(3):
        file_path = mock_context.state["parsed_dir"] / f"file{i}.json"
        file_path.write_text(json.dumps(sample_parsed_data))

    step = AggregateStatsStep()
    step.run(mock_context)

    # Should process all files
    mock_compute_aggregates.assert_called_once()


def test_aggregate_stats_step_missing_required_columns(
    mock_context, mock_settings, mock_compute_aggregates
):
    """Test handling of data missing required columns."""
    # Create data without required columns
    incomplete_data = [{"match_id": "NA1_1", "winner": "blue"}]
    
    file_path = mock_context.state["parsed_dir"] / "incomplete.json"
    file_path.write_text(json.dumps(incomplete_data))

    step = AggregateStatsStep()
    step.run(mock_context)

    # Should add UNKNOWN for missing columns
    mock_compute_aggregates.assert_called_once()
    call_args = mock_compute_aggregates.call_args[0][0]
    assert call_args["region"].iloc[0] == "UNKNOWN"
    assert call_args["tier"].iloc[0] == "UNKNOWN"
    assert call_args["division"].iloc[0] == "UNKNOWN"
    assert call_args["day"].iloc[0] == "UNKNOWN"


def test_aggregate_stats_step_groupby_multiple_groups(
    mock_context, mock_settings, mock_compute_aggregates
):
    """Test grouping by region, tier, division, and day."""
    # Create data with different groups
    data = [
        {
            "region": "NA",
            "tier": "CHALLENGER",
            "division": "I",
            "day": "2024-01-01",
            "winner": "blue",
        },
        {
            "region": "NA",
            "tier": "CHALLENGER",
            "division": "I",
            "day": "2024-01-02",
            "winner": "red",
        },
        {
            "region": "EUW",
            "tier": "GRANDMASTER",
            "division": "I",
            "day": "2024-01-01",
            "winner": "blue",
        },
    ]
    
    file_path = mock_context.state["parsed_dir"] / "multi_group.json"
    file_path.write_text(json.dumps(data))

    step = AggregateStatsStep()
    step.run(mock_context)

    # Should create 3 separate output files
    assert mock_compute_aggregates.call_count == 3


def test_aggregate_stats_step_compute_aggregates_exception(
    mock_context, mock_settings, sample_parsed_data
):
    """Test handling of exception in compute_aggregates."""
    file_path = mock_context.state["parsed_dir"] / "data.json"
    file_path.write_text(json.dumps(sample_parsed_data))

    with patch("app.ingest.steps.aggregate.compute_aggregates") as mock_compute:
        mock_compute.side_effect = Exception("Aggregation error")

        step = AggregateStatsStep()
        step.run(mock_context)

        # Should log error and continue


def test_aggregate_stats_step_output_directory_creation(
    mock_context, mock_settings, sample_parsed_data, mock_compute_aggregates
):
    """Test that output directories are created."""
    file_path = mock_context.state["parsed_dir"] / "data.json"
    file_path.write_text(json.dumps(sample_parsed_data))

    step = AggregateStatsStep()
    step.run(mock_context)

    # Verify directory structure was created
    output_dir = mock_settings.aggregates_root / "NA" / "CHALLENGER" / "I"
    assert output_dir.exists()
    assert output_dir.is_dir()


def test_aggregate_stats_step_json_no_indent(
    mock_context, mock_settings, sample_parsed_data, mock_compute_aggregates
):
    """Test that JSON is written without indentation."""
    file_path = mock_context.state["parsed_dir"] / "data.json"
    file_path.write_text(json.dumps(sample_parsed_data))

    step = AggregateStatsStep()
    step.run(mock_context)

    output_file = mock_settings.aggregates_root / "NA" / "CHALLENGER" / "I" / "2024-01-01.json"
    content = output_file.read_text()
    
    # Should not have indentation (indent=None)
    assert "\n  " not in content


def test_aggregate_stats_step_uses_default_parsed_root(tmp_path, mock_settings):
    """Test using default parsed_root when not in context."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    # Don't set parsed_dir in context
    
    # Create file in default location
    mock_settings.parsed_root.mkdir(parents=True, exist_ok=True)
    file_path = mock_settings.parsed_root / "data.json"
    file_path.write_text("[]")

    step = AggregateStatsStep()
    step.run(context)

    # Should use default parsed_root


def test_aggregate_stats_step_recursive_glob(
    mock_context, mock_settings, sample_parsed_data, mock_compute_aggregates
):
    """Test that files are found recursively."""
    # Create nested directory structure
    nested_file = (
        mock_context.state["parsed_dir"]
        / "level1"
        / "level2"
        / "level3"
        / "data.json"
    )
    nested_file.parent.mkdir(parents=True, exist_ok=True)
    nested_file.write_text(json.dumps(sample_parsed_data))

    step = AggregateStatsStep()
    step.run(mock_context)

    # Should find and process nested file
    mock_compute_aggregates.assert_called_once()


def test_aggregate_stats_step_non_list_data(mock_context, mock_settings):
    """Test handling of JSON that's not a list."""
    # Create file with dict instead of list
    file_path = mock_context.state["parsed_dir"] / "dict.json"
    file_path.write_text('{"key": "value"}')

    step = AggregateStatsStep()
    step.run(mock_context)

    # Should skip non-list data


def test_aggregate_stats_step_dataframe_exception(mock_context, mock_settings):
    """Test handling of DataFrame creation exception."""
    # Create file with data that can't be converted to DataFrame
    file_path = mock_context.state["parsed_dir"] / "bad_data.json"
    file_path.write_text('[{"nested": {"too": {"deep": "value"}}}]')

    step = AggregateStatsStep()
    step.run(mock_context)

    # Should handle gracefully (may or may not raise depending on pandas)


def test_aggregate_stats_step_glob_exception(mock_context, mock_settings):
    """Test handling of exception during file globbing/loading."""
    # Mock glob to raise an exception
    with patch.object(Path, "glob") as mock_glob:
        mock_glob.side_effect = Exception("Glob error")

        step = AggregateStatsStep()
        step.run(mock_context)

        # Should handle exception gracefully and return
