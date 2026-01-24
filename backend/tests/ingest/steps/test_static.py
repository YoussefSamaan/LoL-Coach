import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from app.ingest.steps.static import FetchStaticDataStep
from app.ingest.pipeline import PipelineContext


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock pipeline context."""
    return PipelineContext(run_id="test_run", base_dir=tmp_path)


@pytest.fixture
def mock_settings(tmp_path):
    """Mock settings."""
    with patch("app.ingest.steps.static.settings") as mock:
        mock.ingest.should_fetch_champion_map = True
        mock.champion_map_path = tmp_path / "champion_map.json"
        yield mock


@pytest.fixture
def mock_ddragon_client():
    """Mock DataDragonClient."""
    with patch("app.ingest.steps.static.DataDragonClient") as MockClient:
        client_instance = Mock()
        MockClient.return_value = client_instance
        yield client_instance


def test_fetch_static_data_step_name():
    """Test that the step has the correct name."""
    step = FetchStaticDataStep()
    assert step.name == "Static Data"


def test_fetch_static_data_step_fetch_enabled_file_not_exists(
    mock_context, mock_settings, mock_ddragon_client
):
    """Test fetching when enabled and file doesn't exist."""
    step = FetchStaticDataStep()
    step.run(mock_context)

    # Verify parent directory was created
    assert mock_settings.champion_map_path.parent.exists()

    # Verify client was created and save_champion_map was called
    mock_ddragon_client.save_champion_map.assert_called_once_with(
        mock_settings.champion_map_path
    )

    # Verify champion_map_path was added to context
    assert mock_context.state["champion_map_path"] == mock_settings.champion_map_path


def test_fetch_static_data_step_fetch_enabled_file_exists(
    mock_context, mock_settings, mock_ddragon_client
):
    """Test fetching when enabled and file already exists."""
    # Create existing file
    mock_settings.champion_map_path.parent.mkdir(parents=True, exist_ok=True)
    mock_settings.champion_map_path.write_text('{"1": "Annie"}')

    step = FetchStaticDataStep()
    step.run(mock_context)

    # Should still call save_champion_map (overwrites existing)
    mock_ddragon_client.save_champion_map.assert_called_once_with(
        mock_settings.champion_map_path
    )

    assert mock_context.state["champion_map_path"] == mock_settings.champion_map_path


def test_fetch_static_data_step_fetch_disabled_file_exists(
    mock_context, mock_settings, mock_ddragon_client
):
    """Test when fetch is disabled but file exists."""
    mock_settings.ingest.should_fetch_champion_map = False
    mock_settings.champion_map_path.parent.mkdir(parents=True, exist_ok=True)
    mock_settings.champion_map_path.write_text('{"1": "Annie"}')

    step = FetchStaticDataStep()
    step.run(mock_context)

    # Should not call client
    mock_ddragon_client.save_champion_map.assert_not_called()

    # Should still set champion_map_path in context
    assert mock_context.state["champion_map_path"] == mock_settings.champion_map_path


def test_fetch_static_data_step_fetch_disabled_file_not_exists(
    mock_context, mock_settings, mock_ddragon_client
):
    """Test when fetch is disabled and file doesn't exist."""
    mock_settings.ingest.should_fetch_champion_map = False

    step = FetchStaticDataStep()
    step.run(mock_context)

    # Should not call client
    mock_ddragon_client.save_champion_map.assert_not_called()

    # Should still set champion_map_path in context (even though file doesn't exist)
    assert mock_context.state["champion_map_path"] == mock_settings.champion_map_path


def test_fetch_static_data_step_creates_parent_directory(
    mock_context, mock_ddragon_client, tmp_path
):
    """Test that parent directory is created when it doesn't exist."""
    with patch("app.ingest.steps.static.settings") as mock_settings:
        mock_settings.ingest.should_fetch_champion_map = True
        # Use nested path so parent doesn't exist
        mock_settings.champion_map_path = tmp_path / "data" / "champion_map.json"
        
        # Ensure parent doesn't exist
        assert not mock_settings.champion_map_path.parent.exists()

        step = FetchStaticDataStep()
        step.run(mock_context)

        # Verify parent directory was created
        assert mock_settings.champion_map_path.parent.exists()
        assert mock_settings.champion_map_path.parent.is_dir()


def test_fetch_static_data_step_nested_directory_creation(
    mock_context, mock_ddragon_client, tmp_path
):
    """Test creation of deeply nested parent directories."""
    with patch("app.ingest.steps.static.settings") as mock_settings:
        mock_settings.ingest.should_fetch_champion_map = True
        mock_settings.champion_map_path = (
            tmp_path / "level1" / "level2" / "level3" / "champion_map.json"
        )

        step = FetchStaticDataStep()
        step.run(mock_context)

        # Verify all parent directories were created
        assert mock_settings.champion_map_path.parent.exists()


def test_fetch_static_data_step_client_instantiation(
    mock_context, mock_settings, mock_ddragon_client
):
    """Test that DataDragonClient is instantiated correctly."""
    with patch("app.ingest.steps.static.DataDragonClient") as MockClient:
        client_instance = Mock()
        MockClient.return_value = client_instance

        step = FetchStaticDataStep()
        step.run(mock_context)

        # Verify client was instantiated
        MockClient.assert_called_once()


def test_fetch_static_data_step_no_fetch_no_client_creation(
    mock_context, mock_settings, mock_ddragon_client
):
    """Test that client is not created when fetch is disabled."""
    mock_settings.ingest.should_fetch_champion_map = False
    mock_settings.champion_map_path.write_text('{"1": "Annie"}')

    with patch("app.ingest.steps.static.DataDragonClient") as MockClient:
        step = FetchStaticDataStep()
        step.run(mock_context)

        # Client should not be instantiated
        MockClient.assert_not_called()
