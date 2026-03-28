"""Tests for ML CLI functions."""

from pathlib import Path
from unittest.mock import patch, MagicMock


from ml.cli import (
    MLPipelineStatus,
    check_artifacts_exist,
    build_artifacts_if_needed,
    load_model,
    run_quick_evaluation,
    run_ml_pipeline,
    run_ml_pipeline_on_startup,
    check_data_changed,
    save_data_hash,
    print_pipeline_report,
    main as cli_main,
)
from ml.training import SmoothingConfig
from ml.training import ArtifactStats


def test_pipeline_status():
    status = MLPipelineStatus()
    d = status.to_dict()
    assert "timestamp" in d
    assert d["artifacts_exist"] is False


@patch("ml.cli.settings")
def test_check_data_changed_no_dir(mock_settings, tmp_path):
    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "nowhere"
    assert check_data_changed() is False


@patch("ml.cli.settings")
def test_check_data_changed_no_files(mock_settings, tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "parsed"
    assert check_data_changed() is False


@patch("ml.cli.settings")
def test_check_data_changed_with_files_new_hash(mock_settings, tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "data.json").write_text("[]")
    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "parsed"
    assert check_data_changed() is True


@patch("ml.cli.settings")
def test_check_data_changed_with_files_same_hash(mock_settings, tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    f = parsed / "data.json"
    f.write_text("[]")

    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "parsed"

    # Generate the save
    save_data_hash()

    assert check_data_changed() is False


@patch("ml.cli.settings", spec=[])
def test_check_data_changed_exception(mock_settings):
    # Force exception
    with patch("ml.cli.Path.exists", side_effect=Exception("Test")):
        assert check_data_changed() is True


@patch("ml.cli.settings")
def test_save_data_hash_no_dir(mock_settings, tmp_path):
    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "nowhere"
    save_data_hash()  # Should return without error


@patch("ml.cli.settings")
def test_save_data_hash_exception(mock_settings):
    mock_settings.data_root = None
    save_data_hash()  # Handles exception


@patch("ml.cli.ModelRegistry")
def test_check_artifacts_exist_success(mock_reg):
    mock_instance = MagicMock()
    mock_instance.get_current_version.return_value = MagicMock(run_id="123")
    mock_reg.return_value = mock_instance
    assert check_artifacts_exist() is True


@patch("ml.cli.ModelRegistry")
def test_check_artifacts_exist_none(mock_reg):
    mock_instance = MagicMock()
    mock_instance.get_current_version.return_value = None
    mock_reg.return_value = mock_instance
    assert check_artifacts_exist() is False


@patch("ml.cli.ModelRegistry", side_effect=Exception("Failed"))
def test_check_artifacts_exist_error(mock_reg):
    assert check_artifacts_exist() is False


@patch("ml.cli.settings")
def test_build_artifacts_no_dir(mock_settings, tmp_path):
    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "nowhere"
    success, _ = build_artifacts_if_needed()
    assert success is False


@patch("ml.cli.build_tables")
@patch("ml.cli.settings")
def test_build_artifacts_success(mock_settings, mock_build, tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "data.json").write_text("[]")
    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "parsed"
    mock_settings.ml_pipeline.build.min_samples = 42
    mock_build.return_value = "run_123"

    success, run_id = build_artifacts_if_needed(force=True)
    assert success is True
    assert run_id == "run_123"
    mock_build.assert_called_once()
    build_config = mock_build.call_args.args[0]
    assert isinstance(build_config, SmoothingConfig)
    assert build_config.min_samples == 42


@patch("ml.cli.build_tables", side_effect=Exception("Test"))
@patch("ml.cli.settings")
def test_build_artifacts_error(mock_settings, mock_build, tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "data.json").write_text("[]")
    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "parsed"

    success, _ = build_artifacts_if_needed(force=True)
    assert success is False


@patch("ml.cli.ModelRegistry")
def test_load_model_success(mock_reg):
    mock_instance = MagicMock()
    mock_bundle = MagicMock()
    mock_bundle.stats = ArtifactStats(
        global_winrates={}, role_strength={}, synergy={}, counter={}
    )
    mock_instance.load_latest.return_value = mock_bundle
    mock_reg.return_value = mock_instance

    model, info = load_model()
    assert model is not None
    assert info["model_type"] == "table_based"


@patch("ml.cli.ModelRegistry", side_effect=Exception("Test"))
def test_load_model_error(mock_reg):
    model, info = load_model()
    assert model is None
    assert info == {}


@patch("ml.cli.load_parsed_matches")
@patch("ml.cli.settings")
def test_run_quick_evaluation_no_matches(mock_settings, mock_load):
    mock_load.return_value = []
    assert run_quick_evaluation(MagicMock()) == {}


@patch("ml.cli.evaluate_model")
@patch("ml.cli.split_data")
@patch("ml.cli.load_parsed_matches")
@patch("ml.cli.settings")
def test_run_quick_evaluation_success(mock_settings, mock_load, mock_split, mock_eval):
    mock_load.return_value = [{"match": 1}, {"match": 2}]
    mock_split.return_value = ([{"match": 1}], [{"match": 2}])
    mock_eval.return_value = {"recall@10": 1.0}

    res = run_quick_evaluation(MagicMock())
    assert res["recall@10"] == 1.0


@patch("ml.cli.load_parsed_matches", side_effect=Exception("Test"))
@patch("ml.cli.settings")
def test_run_quick_evaluation_error(mock_settings, mock_load):
    assert run_quick_evaluation(MagicMock()) == {}


@patch("ml.cli.print_pipeline_report")
@patch("ml.cli.run_ml_pipeline")
def test_run_ml_pipeline_on_startup_env_skip(mock_run, mock_print, monkeypatch):
    monkeypatch.setenv("SKIP_ML_PIPELINE", "true")
    status = run_ml_pipeline_on_startup()
    assert len(status.warnings) > 0
    mock_run.assert_not_called()


@patch("ml.cli.settings")
@patch("ml.cli.run_ml_pipeline")
def test_run_ml_pipeline_on_startup_success(
    mock_run, mock_settings, monkeypatch, tmp_path
):
    monkeypatch.setenv("SKIP_ML_PIPELINE", "false")
    monkeypatch.setenv("FORCE_REBUILD", "true")
    monkeypatch.setenv("SKIP_EVALUATION", "true")

    mock_settings.ml_pipeline.reporting.log_to_console = False
    mock_settings.ml_pipeline.reporting.save_to_file = True
    mock_settings.data_root = tmp_path

    mock_status = MLPipelineStatus()
    mock_run.return_value = mock_status

    status = run_ml_pipeline_on_startup()
    assert status == mock_status
    assert (tmp_path / "ml_pipeline_status.json").exists()


@patch("ml.cli.run_ml_pipeline", side_effect=Exception("Test"))
def test_run_ml_pipeline_on_startup_error(mock_run, monkeypatch):
    monkeypatch.setenv("SKIP_ML_PIPELINE", "false")
    status = run_ml_pipeline_on_startup()
    assert len(status.errors) > 0


@patch("ml.cli.settings")
@patch("ml.cli.check_data_changed")
@patch("ml.cli.check_artifacts_exist")
@patch("ml.cli.build_artifacts_if_needed")
@patch("ml.cli.load_model")
@patch("ml.cli.run_quick_evaluation")
def test_run_ml_pipeline_full(
    mock_eval, mock_load, mock_build, mock_artifacts, mock_changed, mock_settings
):
    mock_settings.ml_pipeline.build.force_rebuild = False
    mock_settings.ml_pipeline.evaluation.enabled = True
    mock_settings.ml_pipeline.evaluation.max_samples = 10
    mock_settings.ml_pipeline.stages.build_artifacts = True
    mock_settings.ml_pipeline.stages.load_model = True
    mock_settings.ml_pipeline.stages.evaluate = True

    mock_changed.return_value = False
    mock_artifacts.return_value = True
    mock_load.return_value = (MagicMock(), {"model_type": "table_based"})
    mock_eval.return_value = {"recall@10": 1.0}

    status = run_ml_pipeline()
    assert status.artifacts_exist is True
    assert status.model_loaded is True
    assert status.evaluation_run is True


@patch("ml.cli.settings")
@patch("ml.cli.check_data_changed")
@patch("ml.cli.build_artifacts_if_needed")
def test_run_ml_pipeline_build_error(mock_build, mock_changed, mock_settings):
    mock_settings.ml_pipeline.build.force_rebuild = False
    mock_settings.ml_pipeline.stages.build_artifacts = True

    # Trigger rebuild
    mock_changed.return_value = True
    mock_build.return_value = (False, "Build failed")

    status = run_ml_pipeline()
    assert "Build failed" in status.errors


@patch("ml.cli.settings")
@patch("ml.cli.check_artifacts_exist")
def test_run_ml_pipeline_build_disabled(mock_artifacts, mock_settings):
    mock_settings.ml_pipeline.build.force_rebuild = True
    mock_settings.ml_pipeline.stages.build_artifacts = False

    status = run_ml_pipeline()
    assert "Artifact building disabled but artifacts may be missing" in status.warnings


@patch("ml.cli.settings")
@patch("ml.cli.check_artifacts_exist")
def test_run_ml_pipeline_load_disabled(mock_artifacts, mock_settings):
    mock_settings.ml_pipeline.build.force_rebuild = False
    mock_settings.ml_pipeline.stages.build_artifacts = False
    mock_settings.ml_pipeline.stages.load_model = False

    mock_artifacts.return_value = True
    status = run_ml_pipeline()
    assert "Model loading disabled" in status.warnings


@patch("ml.cli.settings")
@patch("ml.cli.check_artifacts_exist")
@patch("ml.cli.load_model")
def test_run_ml_pipeline_load_error(mock_load, mock_artifacts, mock_settings):
    mock_settings.ml_pipeline.build.force_rebuild = False
    mock_settings.ml_pipeline.stages.build_artifacts = False
    mock_settings.ml_pipeline.stages.load_model = True

    mock_artifacts.return_value = True
    mock_load.return_value = (None, {})
    status = run_ml_pipeline()
    assert "Failed to load model" in status.errors


def test_print_pipeline_report():
    status = MLPipelineStatus()
    status.artifacts_exist = True
    status.artifacts_built = True
    status.model_loaded = True
    status.evaluation_run = True
    status.model_info = {
        "model_type": "table_based",
        "num_champions": 10,
        "num_roles": 5,
    }
    status.metrics = {
        "num_samples": 100,
        "recall@10": 1.0,
        "ndcg@10": 1.0,
        "score_correlation": {"decile_9": {"mean_winrate": 0.9, "count": 10}},
    }
    status.warnings = ["Test warning"]
    status.errors = ["Test error"]
    print_pipeline_report(status)


@patch("ml.cli.run_ml_pipeline")
@patch("ml.cli.print_pipeline_report")
@patch("sys.argv", ["ml/src/ml/cli.py"])
@patch("ml.cli.settings")
def test_cli_main_default(mock_settings, mock_print, mock_run):
    status = MLPipelineStatus()
    mock_run.return_value = status
    cli_main()


@patch("ml.cli.run_ml_pipeline")
@patch("ml.cli.print_pipeline_report")
@patch(
    "sys.argv",
    [
        "ml/src/ml/cli.py",
        "--force-rebuild",
        "--skip-evaluation",
        "--eval-samples",
        "100",
    ],
)
@patch("ml.cli.settings")
def test_cli_main_args(mock_settings, mock_print, mock_run):
    status = MLPipelineStatus()
    mock_run.return_value = status
    cli_main()


@patch("sys.exit")
@patch("ml.cli.run_ml_pipeline")
@patch("ml.cli.print_pipeline_report")
@patch("sys.argv", ["ml/src/ml/cli.py"])
@patch("ml.cli.settings")
def test_cli_main_exit(mock_settings, mock_print, mock_run, mock_exit):
    status = MLPipelineStatus()
    status.errors.append("test error")
    mock_run.return_value = status
    cli_main()
    mock_exit.assert_called_once_with(1)


@patch("ml.cli.settings")
@patch("ml.cli.check_data_changed")
@patch("ml.cli.check_artifacts_exist")
@patch("ml.cli.build_tables")
@patch("ml.cli.save_data_hash")
@patch("ml.cli.load_model")
@patch("ml.cli.run_quick_evaluation")
def test_cli_coverage_branches(
    mock_eval,
    mock_load,
    mock_save,
    mock_build,
    mock_artifacts,
    mock_changed,
    mock_settings,
):
    # Setup for should_rebuild=True, success=True, evaluation empty
    mock_settings.ml_pipeline.build.force_rebuild = True
    mock_settings.ml_pipeline.stages.build_artifacts = True
    mock_settings.ml_pipeline.stages.load_model = True
    mock_settings.ml_pipeline.stages.evaluate = True

    # Path exists but evaluate fails
    mock_settings.data_root = Path("/tmp/mock")
    mock_settings.ingest.paths.parsed_dir = "parsed"

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.rglob", return_value=[Path("a.json")]),
    ):
        mock_build.return_value = "run_999"
        mock_load.return_value = (MagicMock(), {})
        mock_eval.return_value = {}  # empty metrics

        status = run_ml_pipeline()
        assert status.artifacts_built is True
        mock_save.assert_called_once()
        assert "Evaluation produced no results" in status.warnings

        # Test evaluation returning results and hitting Model was just trained warning
        mock_eval.return_value = {"recall": 1.0}
        status2 = run_ml_pipeline()
        assert any("Model was just trained" in w for w in status2.warnings)

    # Test evaluation disabled in config
    mock_settings.ml_pipeline.stages.evaluate = False
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.rglob", return_value=[Path("a.json")]),
    ):
        mock_build.return_value = "run_999"
        mock_load.return_value = (MagicMock(), {})
        status = run_ml_pipeline()
        assert status.evaluation_run is False

    # Test evaluation skipped by flag
    mock_settings.ml_pipeline.stages.evaluate = True
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.rglob", return_value=[Path("a.json")]),
    ):
        mock_build.return_value = "run_999"
        mock_load.return_value = (MagicMock(), {})
        status = run_ml_pipeline(skip_evaluation=True)
        assert status.evaluation_run is False


@patch("ml.cli.settings")
@patch("ml.cli.run_ml_pipeline")
def test_run_ml_pipeline_on_startup_console_log(mock_run, mock_settings):
    mock_settings.ml_pipeline.reporting.log_to_console = True
    mock_settings.ml_pipeline.reporting.save_to_file = False

    status = MLPipelineStatus()
    mock_run.return_value = status

    # Run without patching print_pipeline_report so the actual line executes
    res = run_ml_pipeline_on_startup()
    assert res == status
