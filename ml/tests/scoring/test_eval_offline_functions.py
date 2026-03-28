"""Tests for ml.scoring.eval_offline functions."""

import json
from unittest.mock import patch, MagicMock

import pytest

from ml.scoring.eval_offline import (
    load_parsed_matches,
    split_data,
    evaluate_model,
    main as eval_main,
)
from ml.models.table_based import TableBasedModel
from ml.training import ArtifactStats


@pytest.fixture
def sample_matches():
    blue = [
        {"c": "Garen", "r": "TOP"},
        {"c": "LeeSin", "r": "JUNGLE"},
        {"c": "Ahri", "r": "MID"},
        {"c": "Jinx", "r": "ADC"},
        {"c": "Thresh", "r": "SUPPORT"},
    ]
    red = [
        {"c": "Darius", "r": "TOP"},
        {"c": "Amumu", "r": "JUNGLE"},
        {"c": "Zed", "r": "MID"},
        {"c": "Ashe", "r": "ADC"},
        {"c": "Lux", "r": "SUPPORT"},
    ]
    return [
        {
            "match_id": "1",
            "blue_team": json.dumps(blue),
            "red_team": json.dumps(red),
            "winner": "BLUE",
        },
        {
            "match_id": "2",
            "blue_team": json.dumps(blue),
            "red_team": json.dumps(red),
            "winner": "RED",
        },
    ]


@pytest.fixture
def mock_model():
    stats = ArtifactStats(
        global_winrates={"Ahri": 0.5, "Zed": 0.5, "Lux": 0.5, "Syndra": 0.5},
        role_strength={"MID": {"Ahri": 0.5, "Zed": 0.5, "Lux": 0.5, "Syndra": 0.5}},
        synergy={},
        counter={},
    )
    # Instantiate actual TableBasedModel so isinstance check passes
    model = TableBasedModel(stats=stats)

    # Mock predict method to return predictable results
    def side_effect(role, allies, enemies, candidates, **kwargs):
        from ml.models.base import DraftPrediction

        preds = []
        for c in candidates:
            score = 1.0 if c == "Ahri" or c == "Syndra" else 0.5
            preds.append(DraftPrediction(champion=c, score=score, reasons=[]))
        return sorted(preds, key=lambda p: p.score, reverse=True)

    model.predict = MagicMock(side_effect=side_effect)
    return model


def test_load_parsed_matches(tmp_path):
    d = tmp_path / "parsed"
    d.mkdir()

    (d / "match1.json").write_text('[{"id": 1}]')
    (d / "match2.json").write_text('{"id": 2}')
    (d / "bad.json").write_text("{bad")

    matches = load_parsed_matches(d)
    assert len(matches) == 2


def test_split_data(sample_matches):
    train, test = split_data(sample_matches, train_ratio=0.5, seed=42)
    assert len(train) == 1
    assert len(test) == 1


def test_evaluate_model(mock_model, sample_matches):
    res = evaluate_model(mock_model, sample_matches, k=10)
    assert "recall@10" in res
    assert "ndcg@10" in res
    assert res["num_samples"] > 0


def test_evaluate_model_exceptions(mock_model):
    res = evaluate_model(mock_model, [{"bad": "data"}])
    assert res["num_samples"] == 0


def test_evaluate_model_max_samples(mock_model, sample_matches):
    res = evaluate_model(mock_model, sample_matches, max_samples=1)
    assert res["num_samples"] == 1


def test_evaluate_model_no_true_pick(mock_model, sample_matches):
    # Modify match to have an empty champion
    matches = json.loads(json.dumps(sample_matches))
    teams = json.loads(matches[0]["blue_team"])
    teams[0]["c"] = ""
    matches[0]["blue_team"] = json.dumps(teams)

    res = evaluate_model(mock_model, matches)
    assert res["num_samples"] > 0


def test_evaluate_model_predict_exception(mock_model, sample_matches):
    mock_model.predict.side_effect = Exception("Test Error")
    res = evaluate_model(mock_model, sample_matches)
    assert res["num_samples"] == 0


def test_evaluate_model_no_candidates_fallback(sample_matches):
    # Pass a MagicMock instead of TableBasedModel so isinstance fails
    mock_generic = MagicMock()
    res = evaluate_model(mock_generic, sample_matches)
    assert res["num_samples"] == 0


def test_evaluate_model_exception_on_candidates(sample_matches):
    from ml.models.table_based import TableBasedModel
    from ml.scoring.eval_offline import evaluate_model

    # Create a real TableBasedModel to pass isinstance check
    real_model = TableBasedModel(stats=MagicMock())

    # Force an exception when resolving the role strength data list
    real_model.stats.role_strength.get.side_effect = Exception("Data Corrupted!")
    res = evaluate_model(real_model, sample_matches)
    assert res["num_samples"] == 0


def test_evaluate_model_arbitrary_exception(mock_model, sample_matches):
    class ExplodingModel(MagicMock):
        def get_model_info(self):
            raise ValueError("Boom")

    bad_model = ExplodingModel()
    res = evaluate_model(bad_model, sample_matches)
    assert res["num_samples"] == 0


@patch("ml.scoring.eval_offline.settings")
@patch("ml.scoring.eval_offline.argparse.ArgumentParser.parse_args")
def test_main_no_dir(mock_args, mock_settings, tmp_path):
    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "nowhere"
    mock_args.return_value = MagicMock(
        run_id=None, split=0.8, no_split=False, k=10, max_samples=10, seed=42
    )

    # Should exit early without raising exception
    eval_main()


@patch("ml.scoring.eval_offline.settings")
@patch("ml.scoring.eval_offline.argparse.ArgumentParser.parse_args")
def test_main_no_matches(mock_args, mock_settings, tmp_path):
    d = tmp_path / "parsed"
    d.mkdir()

    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "parsed"

    args = MagicMock(
        run_id=None, split=0.8, no_split=False, k=10, max_samples=10, seed=42
    )
    mock_args.return_value = args

    with patch("ml.registry.ModelRegistry") as mock_reg:
        mock_instance = MagicMock()
        mock_bundle = MagicMock()
        mock_bundle.stats = ArtifactStats(
            global_winrates={}, role_strength={}, synergy={}, counter={}
        )
        mock_instance.load_latest.return_value = mock_bundle
        mock_reg.return_value = mock_instance

        eval_main()


@patch("ml.scoring.eval_offline.settings")
@patch("ml.scoring.eval_offline.argparse.ArgumentParser.parse_args")
def test_main_success_no_split(mock_args, mock_settings, tmp_path):
    d = tmp_path / "parsed"
    d.mkdir()
    (d / "m.json").write_text(
        '[{"match_id": "1", "blue_team": [], "red_team": [], "winner": "BLUE"}]'
    )

    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "parsed"
    mock_settings.artifacts_path = tmp_path / "artifacts"

    args = MagicMock(
        run_id="model_v1", split=0.8, no_split=True, k=10, max_samples=10, seed=42
    )
    mock_args.return_value = args

    with patch("ml.models.table_based.TableBasedModel.load") as mock_load:
        mock_model = MagicMock()
        mock_load.return_value = mock_model

        with patch("ml.scoring.eval_offline.evaluate_model") as mock_eval:
            mock_eval.return_value = {
                "recall@10": 1.0,
                "ndcg@10": 1.0,
                "num_samples": 1,
                "score_correlation": {},
            }
            eval_main()

    assert (tmp_path / "eval_results.json").exists()


@patch("ml.scoring.eval_offline.settings")
@patch("ml.scoring.eval_offline.argparse.ArgumentParser.parse_args")
def test_main_success_split(mock_args, mock_settings, tmp_path):
    d = tmp_path / "parsed"
    d.mkdir()
    (d / "m.json").write_text(
        '[{"match_id": "1", "blue_team": [], "red_team": [], "winner": "BLUE"}]'
    )

    mock_settings.data_root = tmp_path
    mock_settings.ingest.paths.parsed_dir = "parsed"

    args = MagicMock(
        run_id=None, split=0.8, no_split=False, k=10, max_samples=10, seed=42
    )
    mock_args.return_value = args

    with patch("ml.registry.ModelRegistry") as mock_reg:
        mock_instance = MagicMock()
        mock_bundle = MagicMock()
        mock_bundle.stats = ArtifactStats(
            global_winrates={}, role_strength={}, synergy={}, counter={}
        )
        mock_instance.load_latest.return_value = mock_bundle
        mock_reg.return_value = mock_instance

        with patch("ml.scoring.eval_offline.evaluate_model") as mock_eval:
            mock_eval.return_value = {
                "recall@10": 1.0,
                "ndcg@10": 1.0,
                "num_samples": 1,
                "score_correlation": {"decile_9": {"mean_winrate": 1.0, "count": 1}},
            }
            eval_main()

    assert (tmp_path / "eval_results.json").exists()
