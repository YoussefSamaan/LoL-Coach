import pytest
import json
from app.ingest.domain.parser import parse_match_row


@pytest.fixture
def id_map():
    return {"1": "Annie", "2": "Olaf"}


@pytest.fixture
def rank_ctx():
    return {"tier": "DIAMOND", "division": "I", "region": "NA"}


def test_parse_match_row_success(id_map, rank_ctx):
    info = {
        "gameMode": "CLASSIC",
        "gameVersion": "14.1.1.99",
        "gameCreation": 1704067200000,
        "participants": [
            {"teamId": 100, "championName": "Annie", "teamPosition": "MIDDLE", "win": True},
            {"teamId": 100, "championName": "Olaf", "teamPosition": "JUNGLE", "win": True},
            {"teamId": 100, "championName": "A", "teamPosition": "TOP", "win": True},
            {"teamId": 100, "championName": "B", "teamPosition": "BOTTOM", "win": True},
            {"teamId": 100, "championName": "C", "teamPosition": "UTILITY", "win": True},
            {"teamId": 200, "championName": "D", "teamPosition": "TOP", "win": False},
            {"teamId": 200, "championName": "E", "teamPosition": "JUNGLE", "win": False},
            {"teamId": 200, "championName": "F", "teamPosition": "MIDDLE", "win": False},
            {"teamId": 200, "championName": "G", "teamPosition": "BOTTOM", "win": False},
            {"teamId": 200, "championName": "H", "teamPosition": "UTILITY", "win": False},
        ],
        "teams": [
            {"teamId": 100, "bans": [{"championId": 2}]},  # Ban Olaf
            {"teamId": 200, "bans": []},
        ],
    }

    data = {"metadata": {"matchId": "NA1_123"}, "info": info}

    result = parse_match_row(data, id_map, rank_ctx)

    assert result["match_id"] == "NA1_123"
    assert result["day"] == "2024-01-01"
    assert result["patch"] == "14.1"
    assert len(json.loads(result["blue_team"])) == 5
    assert len(json.loads(result["red_team"])) == 5
    assert result["blue_bans"] == ["Olaf"]


def test_parse_match_row_invalid_mode(id_map, rank_ctx):
    data = {"info": {"gameMode": "ARAM"}}
    assert parse_match_row(data, id_map, rank_ctx) is None


def test_parse_match_row_incomplete_teams(id_map, rank_ctx):
    info = {
        "gameMode": "CLASSIC",
        "participants": [{"teamId": 100, "championName": "Annie", "teamPosition": "MIDDLE"}],
    }
    data = {"metadata": {"matchId": "M1"}, "info": info}
    assert parse_match_row(data, id_map, rank_ctx) is None


def test_parse_match_row_invalid_roles(id_map, rank_ctx):
    # Invalid position should be skipped, leading to incomplete team
    info = {
        "gameMode": "CLASSIC",
        "participants": [{"teamId": 100, "championName": "Annie", "teamPosition": "INVALID"}],
    }
    data = {"metadata": {"matchId": "M1"}, "info": info}

    # We expect warning log (though not strictly asserting log call here unless we patch logger)
    # Result should be None bc team len < 5
    assert parse_match_row(data, id_map, rank_ctx) is None


def test_parse_match_row_missing_bans_map(rank_ctx):
    # Map missing ID '999'
    info = {
        "gameMode": "CLASSIC",
        "participants": 5 * [{"teamId": 100, "championName": "A", "teamPosition": "TOP"}]
        + 5 * [{"teamId": 200, "championName": "B", "teamPosition": "TOP"}],
        "teams": [{"teamId": 100, "bans": [{"championId": 999}]}],
    }

    # Minimal Valid Team
    blue = [{"teamId": 100, "championName": "A", "teamPosition": "TOP", "win": True}] * 5
    red = [{"teamId": 200, "championName": "B", "teamPosition": "TOP", "win": False}] * 5

    info["participants"] = blue + red
    data = {"metadata": {"matchId": "M1"}, "info": info}

    result = parse_match_row(data, {}, rank_ctx)  # Empty ID map
    assert result["blue_bans"] == []  # Should be empty, warning logged
