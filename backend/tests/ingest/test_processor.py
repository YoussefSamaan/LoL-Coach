import json
import pytest
import pandas as pd
from app.ingest.processor import MatchProcessor


@pytest.fixture
def champ_map_file(tmp_path):
    f = tmp_path / "map.json"
    f.write_text(json.dumps({"1": "Annie", "2": "Olaf"}), encoding="utf-8")
    return f


def test_init_loads_map(champ_map_file):
    proc = MatchProcessor(champ_map_file)
    assert proc.id_map["1"] == "Annie"


def test_init_missing_map(tmp_path):
    # Should not crash
    proc = MatchProcessor(tmp_path / "missing.json")
    assert proc.id_map == {}


def test_parse_match_row_classic(champ_map_file):
    proc = MatchProcessor(champ_map_file)

    data = {
        "metadata": {"matchId": "M1"},
        "info": {
            "gameMode": "CLASSIC",
            "gameCreation": 1000,
            "teams": [
                {"teamId": 100, "win": True, "bans": [{"championId": 1}]},
                {"teamId": 200, "win": False, "bans": [{"championId": 2}]},
            ],
            "participants": [
                {"teamId": 100, "teamPosition": "TOP", "championName": "Garen", "win": True},
                {"teamId": 200, "teamPosition": "JUNGLE", "championName": "LeeSin", "win": False},
            ],
        },
    }

    row = proc.parse_match_row(data)
    assert row["match_id"] == "M1"
    assert row["blue_win"] is True
    assert row["blue_top"] == "Garen"
    assert row["red_jungle"] == "LeeSin"
    assert "Annie" in row["blue_bans"]
    assert "Olaf" in row["red_bans"]


def test_parse_match_row_aram(champ_map_file):
    proc = MatchProcessor(champ_map_file)
    data = {"info": {"gameMode": "ARAM"}}
    assert proc.parse_match_row(data) is None


def test_process_dir(champ_map_file, tmp_path):
    proc = MatchProcessor(champ_map_file)

    in_dir = tmp_path / "raw"
    in_dir.mkdir()

    # Valid file
    valid_data = {
        "metadata": {"matchId": "M1"},
        "info": {"gameMode": "CLASSIC", "gameCreation": 2000000, "teams": [], "participants": []},
    }
    (in_dir / "valid.json").write_text(json.dumps(valid_data))

    # Invalid file (broken json)
    (in_dir / "bad.json").write_text("{ broken")

    out_file = tmp_path / "out.parquet"

    proc.process_dir(in_dir, out_file)

    assert out_file.exists()
    df = pd.read_parquet(out_file)
    assert len(df) == 1
    assert df.iloc[0]["match_id"] == "M1"


def test_process_dir_csv(champ_map_file, tmp_path):
    proc = MatchProcessor(champ_map_file)
    in_dir = tmp_path / "raw_csv"
    in_dir.mkdir()

    valid_data = {"metadata": {"matchId": "M1"}, "info": {"gameMode": "CLASSIC"}}
    (in_dir / "valid.json").write_text(json.dumps(valid_data))

    out_file = tmp_path / "out.csv"
    proc.process_dir(in_dir, out_file, fmt="csv")

    assert out_file.exists()
    content = out_file.read_text()
    assert "M1" in content


def test_init_bad_map(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json")
    proc = MatchProcessor(f)
    assert proc.id_map == {}


def test_process_dir_min_time(champ_map_file, tmp_path):
    proc = MatchProcessor(champ_map_file)
    in_dir = tmp_path / "raw_time"
    in_dir.mkdir()

    # Old match
    data = {"info": {"gameCreation": 1000000000000}}  # 1000... sec
    (in_dir / "old.json").write_text(json.dumps(data))

    out_file = tmp_path / "out.parquet"

    # Filter min_time > match time
    proc.process_dir(in_dir, out_file, min_time=2000000000)

    # Should result in "No valid match entries found" and return early (no file created)
    # The code logs warning but returns.
    assert not out_file.exists()


def test_process_dir_read_fail(champ_map_file, tmp_path):
    proc = MatchProcessor(champ_map_file)
    in_dir = tmp_path / "raw_fail"
    in_dir.mkdir()

    (in_dir / "ok.json").write_text('{"bad": "json"}')
    # This will fail json.loads and be caught by 'except Exception: pass'

    out_file = tmp_path / "out_fail.parquet"
    proc.process_dir(in_dir, out_file)
    assert not out_file.exists()


def test_game_mode_skip(champ_map_file):
    proc = MatchProcessor(champ_map_file)
    row = proc.parse_match_row({"info": {"gameMode": "ARAM"}})
    assert row is None
