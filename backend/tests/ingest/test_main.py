import sys
from unittest.mock import patch
from app.ingest.main import main


@patch("app.ingest.main.IngestPipeline")
@patch("app.ingest.main.settings")
def test_main_execution(mock_settings, MockPipeline):
    # Setup mocks
    mock_settings.data_root = "data"
    pipeline_instance = MockPipeline.return_value

    # Mock CLI args
    test_args = ["main.py", "--since", "12345", "--note", "test_run"]
    with patch.object(sys, "argv", test_args):
        ret = main()

    assert ret == 0
    assert pipeline_instance.add_step.call_count >= 5
    pipeline_instance.execute.assert_called_once()

    context_arg = pipeline_instance.execute.call_args[0][0]
    assert context_arg.state["min_match_time"] == 12345


@patch("app.ingest.main.IngestPipeline")
def test_main_failure(MockPipeline):
    pipeline_instance = MockPipeline.return_value
    pipeline_instance.execute.side_effect = Exception("Pipeline Crash")

    with patch.object(sys, "argv", ["main.py"]):
        ret = main()

    assert ret == 1


@patch("app.ingest.main.IngestPipeline")
def test_main_cleanup_flag(MockPipeline):
    pipeline_instance = MockPipeline.return_value

    with patch.object(sys, "argv", ["main.py", "--cleanup-raw"]):
        main()

    assert pipeline_instance.add_step.call_count == 7


def test_main_skip_download_stages(tmp_path):
    """Test main.py logic when download is skipped but parse is enabled."""
    from unittest.mock import MagicMock

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.raw_dir = "raw"

    # stages: download=False, parse=True
    mock_settings.ingest.stages.fetch = False
    mock_settings.ingest.stages.scan = False
    mock_settings.ingest.stages.download = False
    mock_settings.ingest.stages.parse = True
    mock_settings.ingest.stages.aggregate = False

    with (
        patch("app.ingest.main.settings", mock_settings),
        patch("app.ingest.main.IngestPipeline") as MockPipeline,
    ):
        pipeline_instance = MockPipeline.return_value

        # Mock arg parser
        with patch("argparse.ArgumentParser.parse_args") as mock_args:
            mock_args.return_value = MagicMock(
                cleanup_raw=False, since=0, format="parquet", note=""
            )

            main()

            # Verify context state had raw_dir set
            # access pipeline.execute(context) call
            assert pipeline_instance.execute.called
            context = pipeline_instance.execute.call_args[0][0]

            assert "raw_dir" in context.state
            assert context.state["raw_dir"] == tmp_path / "raw"
