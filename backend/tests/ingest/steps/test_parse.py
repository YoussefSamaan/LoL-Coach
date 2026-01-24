import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path
from app.ingest.steps.parse import ParseMatchStep
from app.ingest.pipeline import PipelineContext


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock pipeline context."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    context.state["raw_dir"] = raw_dir
    return context


@pytest.fixture
def mock_settings(tmp_path):
    """Mock settings."""
    with patch("app.ingest.steps.parse.settings") as mock:
        mock.data_root = tmp_path
        mock.ingest.paths.parsed_dir = "parsed"
        mock.ingest.paths.processed_file_type = "json"
        mock.champion_map_path = tmp_path / "champion_map.json"
        yield mock


@pytest.fixture
def champion_map(tmp_path):
    """Create a champion map file."""
    champion_map_path = tmp_path / "champion_map.json"
    champion_map_data = {"1": "Annie", "2": "Olaf"}
    champion_map_path.write_text(json.dumps(champion_map_data))
    return champion_map_path


@pytest.fixture
def mock_batch_process():
    """Mock batch_process_raw_matches function."""
    with patch("app.ingest.steps.parse.batch_process_raw_matches") as mock:
        yield mock


def test_parse_match_step_name():
    """Test that the step has the correct name."""
    step = ParseMatchStep()
    assert step.name == "Parse Matches"


def test_parse_match_step_no_raw_dir(tmp_path, mock_settings):
    """Test when no raw_dir is in context."""
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    step = ParseMatchStep()
    step.run(context)

    # Should return early without doing anything
    assert "parsed_dir" not in context.state


def test_parse_match_step_success(
    mock_context, mock_settings, champion_map, mock_batch_process
):
    """Test successful parsing of matches."""
    mock_context.state["match_rank_map"] = {
        "NA1_match1": {"tier": "CHALLENGER", "division": "I", "region": "NA"}
    }

    step = ParseMatchStep()
    step.run(mock_context)

    # Verify batch_process was called with correct arguments
    mock_batch_process.assert_called_once()
    call_kwargs = mock_batch_process.call_args[1]
    
    assert call_kwargs["input_dir"] == mock_context.state["raw_dir"]
    assert call_kwargs["output_root"] == mock_settings.data_root / "parsed"
    assert call_kwargs["id_map"] == {"1": "Annie", "2": "Olaf"}
    assert call_kwargs["rank_map"] == mock_context.state["match_rank_map"]
    assert call_kwargs["min_time"] == 0
    assert call_kwargs["output_format"] == "json"

    # Verify parsed_dir was set in context
    assert mock_context.state["parsed_dir"] == mock_settings.data_root / "parsed"


def test_parse_match_step_with_min_time(
    mock_context, mock_settings, champion_map, mock_batch_process
):
    """Test parsing with min_match_time filter."""
    mock_context.state["min_match_time"] = 1704067200

    step = ParseMatchStep()
    step.run(mock_context)

    call_kwargs = mock_batch_process.call_args[1]
    assert call_kwargs["min_time"] == 1704067200


def test_parse_match_step_no_min_time(
    mock_context, mock_settings, champion_map, mock_batch_process
):
    """Test parsing without min_match_time (defaults to 0)."""
    step = ParseMatchStep()
    step.run(mock_context)

    call_kwargs = mock_batch_process.call_args[1]
    assert call_kwargs["min_time"] == 0


def test_parse_match_step_no_champion_map(
    mock_context, mock_settings, mock_batch_process
):
    """Test parsing when champion map doesn't exist."""
    # Champion map doesn't exist
    step = ParseMatchStep()
    step.run(mock_context)

    # Should use empty dict
    call_kwargs = mock_batch_process.call_args[1]
    assert call_kwargs["id_map"] == {}


def test_parse_match_step_champion_map_from_context(
    mock_context, mock_settings, mock_batch_process, tmp_path
):
    """Test that champion_map_path from context is used."""
    custom_map_path = tmp_path / "custom_champion_map.json"
    custom_map_data = {"3": "Twisted Fate"}
    custom_map_path.write_text(json.dumps(custom_map_data))
    
    mock_context.state["champion_map_path"] = custom_map_path

    step = ParseMatchStep()
    step.run(mock_context)

    call_kwargs = mock_batch_process.call_args[1]
    assert call_kwargs["id_map"] == {"3": "Twisted Fate"}


def test_parse_match_step_champion_map_invalid_json(
    mock_context, mock_settings, mock_batch_process, tmp_path
):
    """Test handling of invalid JSON in champion map."""
    bad_map_path = tmp_path / "bad_champion_map.json"
    bad_map_path.write_text("not valid json{")
    
    mock_settings.champion_map_path = bad_map_path

    step = ParseMatchStep()
    step.run(mock_context)

    # Should use empty dict when JSON parsing fails
    call_kwargs = mock_batch_process.call_args[1]
    assert call_kwargs["id_map"] == {}


def test_parse_match_step_no_match_rank_map(
    mock_context, mock_settings, champion_map, mock_batch_process
):
    """Test parsing without match_rank_map (defaults to empty dict)."""
    step = ParseMatchStep()
    step.run(mock_context)

    call_kwargs = mock_batch_process.call_args[1]
    assert call_kwargs["rank_map"] == {}


def test_parse_match_step_creates_output_directory(
    mock_context, mock_settings, champion_map, mock_batch_process
):
    """Test that output directory is created."""
    parsed_dir = mock_settings.data_root / "parsed"
    assert not parsed_dir.exists()

    step = ParseMatchStep()
    step.run(mock_context)

    assert parsed_dir.exists()
    assert parsed_dir.is_dir()


def test_parse_match_step_output_format_csv(
    mock_context, mock_settings, champion_map, mock_batch_process
):
    """Test parsing with CSV output format."""
    mock_settings.ingest.paths.processed_file_type = "csv"

    step = ParseMatchStep()
    step.run(mock_context)

    call_kwargs = mock_batch_process.call_args[1]
    assert call_kwargs["output_format"] == "csv"


def test_parse_match_step_champion_map_encoding(
    mock_context, mock_settings, mock_batch_process, tmp_path
):
    """Test that champion map is read with UTF-8 encoding."""
    # Create map with unicode characters
    unicode_map_path = tmp_path / "unicode_champion_map.json"
    unicode_map_data = {"1": "Aatrox", "2": "Ahri"}
    unicode_map_path.write_text(json.dumps(unicode_map_data), encoding="utf-8")
    
    mock_settings.champion_map_path = unicode_map_path

    step = ParseMatchStep()
    step.run(mock_context)

    call_kwargs = mock_batch_process.call_args[1]
    assert call_kwargs["id_map"] == {"1": "Aatrox", "2": "Ahri"}


def test_parse_match_step_empty_champion_map(
    mock_context, mock_settings, mock_batch_process, tmp_path
):
    """Test parsing with empty champion map."""
    empty_map_path = tmp_path / "empty_champion_map.json"
    empty_map_path.write_text("{}")
    
    mock_settings.champion_map_path = empty_map_path

    step = ParseMatchStep()
    step.run(mock_context)

    call_kwargs = mock_batch_process.call_args[1]
    assert call_kwargs["id_map"] == {}
