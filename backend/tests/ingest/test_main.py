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
