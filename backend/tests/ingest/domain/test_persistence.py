import pytest
import json
from app.ingest.domain.persistence import batch_process_raw_matches


@pytest.fixture
def id_map():
    return {"1": "A"}


@pytest.fixture
def rank_map():
    return {"M1": {"tier": "C", "division": "I", "region": "NA"}}


def test_batch_process_raw_matches(tmp_path, id_map, rank_map):
    in_dir = tmp_path / "raw"
    in_dir.mkdir()

    # Create Mock File: raw/NA/C/I/date/M1.json
    f_dir = in_dir / "NA" / "C" / "I" / "2024-01-01"
    f_dir.mkdir(parents=True)

    raw_data = {
        "metadata": {"matchId": "M1"},
        "info": {
            "gameMode": "CLASSIC",
            "gameCreation": 1704067200000,  # 2024-01-01
            "gameVersion": "14.1",
            "participants": [
                {"teamId": 100, "championName": "A", "teamPosition": "TOP", "win": True}
            ]
            * 5
            + [{"teamId": 200, "championName": "A", "teamPosition": "TOP", "win": False}] * 5,
        },
    }
    (f_dir / "M1.json").write_text(json.dumps(raw_data))

    out_root = tmp_path / "parsed"

    batch_process_raw_matches(in_dir, out_root, id_map, rank_map)

    expected_file = out_root / "NA" / "C" / "I" / "2024-01-01.json"
    assert expected_file.exists()

    content = json.loads(expected_file.read_text())
    assert len(content) == 1
    assert content[0]["match_id"] == "M1"
    assert content[0]["day"] == "2024-01-01"


def test_batch_process_skip_time(tmp_path, id_map, rank_map):
    in_dir = tmp_path / "raw"
    in_dir.mkdir()
    (in_dir / "M1.json").write_text(
        json.dumps(
            {
                "info": {"gameCreation": 1000},  # Ancient time
                "metadata": {"matchId": "M1"},
            }
        )
    )

    out_root = tmp_path / "parsed"
    # Min time = 2000 (seconds) > 1 (seconds from 1000ms)
    batch_process_raw_matches(in_dir, out_root, id_map, rank_map, min_time=2000)

    assert not list(out_root.glob("**/*.json"))


def test_batch_process_duplicates(tmp_path, id_map, rank_map):
    # Setup similar to success case
    in_dir = tmp_path / "raw"
    in_dir.mkdir()
    f_dir = in_dir / "dir"
    f_dir.mkdir()

    match_json = json.dumps(
        {
            "metadata": {"matchId": "M1"},
            "info": {
                "gameMode": "CLASSIC",
                "gameCreation": 1704067200000,
                "participants": [
                    {"teamId": 100, "championName": "A", "teamPosition": "TOP", "win": True}
                ]
                * 5
                + [{"teamId": 200, "championName": "A", "teamPosition": "TOP", "win": False}] * 5,
            },
        }
    )
    (f_dir / "m.json").write_text(match_json)

    out_root = tmp_path / "parsed"
    target = out_root / "NA" / "C" / "I" / "2024-01-01.json"
    target.parent.mkdir(parents=True)

    # Pre-existing file with M1
    target.write_text(json.dumps([{"match_id": "M1"}]))

    batch_process_raw_matches(in_dir, out_root, id_map, rank_map)

    content = json.loads(target.read_text())
    assert len(content) == 1  # Should not duplicate


def test_batch_process_file_read_error(tmp_path, id_map, rank_map):
    in_dir = tmp_path / "raw"
    in_dir.mkdir()
    (in_dir / "bad.json").write_text("invalid json")

    out_root = tmp_path / "parsed"
    batch_process_raw_matches(in_dir, out_root, id_map, rank_map)
    # Should not crash


def test_batch_process_empty_df(tmp_path, id_map, rank_map):
    in_dir = tmp_path / "raw"
    in_dir.mkdir()
    # No files
    out_root = tmp_path / "parsed"
    batch_process_raw_matches(in_dir, out_root, id_map, rank_map)
    # Just prints "Processing 0 matches" and "No valid match entries found"


def test_batch_process_existing_file_corrupt(tmp_path, id_map):
    # Test handling of corrupt existing target file
    # We need to ensure the match ID is in the rank_map so it goes to the expected directory
    rank_map = {"M2": {"tier": "C", "division": "I", "region": "NA"}}

    in_dir = tmp_path / "raw"
    in_dir.mkdir()
    f_dir = in_dir / "dir"
    f_dir.mkdir()

    match_json = json.dumps(
        {
            "metadata": {"matchId": "M2"},
            "info": {
                "gameMode": "CLASSIC",
                "gameCreation": 1704067200000,
                "participants": [
                    {"teamId": 100, "championName": "A", "teamPosition": "TOP", "win": True}
                ]
                * 5
                + [{"teamId": 200, "championName": "A", "teamPosition": "TOP", "win": False}] * 5,
            },
        }
    )
    (f_dir / "m2.json").write_text(match_json)

    out_root = tmp_path / "parsed"
    target = out_root / "NA" / "C" / "I" / "2024-01-01.json"
    target.parent.mkdir(parents=True)
    target.write_text("bad json")  # Corrupt

    batch_process_raw_matches(in_dir, out_root, id_map, rank_map)

    # Should overwrite/append correctly (treating existing as empty)
    content = json.loads(target.read_text())
    assert len(content) == 1
    assert content[0]["match_id"] == "M2"


def test_batch_process_save_exception(tmp_path, id_map, rank_map):
    # Create valid input to populate DataFrame
    in_dir = tmp_path / "raw"
    in_dir.mkdir()
    f_dir = in_dir / "dir"
    f_dir.mkdir()

    match_json = json.dumps(
        {
            "metadata": {"matchId": "M1"},
            "info": {
                "gameMode": "CLASSIC",
                "gameCreation": 1704067200000,
                "participants": [
                    {"teamId": 100, "championName": "A", "teamPosition": "TOP", "win": True}
                ]
                * 5
                + [{"teamId": 200, "championName": "A", "teamPosition": "TOP", "win": False}] * 5,
            },
        }
    )
    (f_dir / "m.json").write_text(match_json)

    # Mock output_root to be a file so mkdir fails
    bad_root = tmp_path / "file"
    bad_root.touch()

    # This should trigger exception in the save loop
    batch_process_raw_matches(in_dir, bad_root, id_map, rank_map)
    # Should be caught and logged
