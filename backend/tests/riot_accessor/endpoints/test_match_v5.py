from unittest.mock import MagicMock

from app.domain.enums import Region
from app.riot_accessor.endpoints.match_v5 import get_match, list_match_ids_by_puuid


def test_list_match_ids_by_puuid():
    mock_client = MagicMock()
    mock_client.get_json.return_value = ["match1", "match2"]

    result = list_match_ids_by_puuid(client=mock_client, region=Region.NA, puuid="some-puuid")

    assert result == ["match1", "match2"]
    mock_client.get_json.assert_called_once()
    # NA regional host is americas
    assert "americas.api" in mock_client.get_json.call_args[1]["url"]
    assert "matches/by-puuid/some-puuid/ids" in mock_client.get_json.call_args[1]["url"]


def test_get_match():
    mock_client = MagicMock()
    mock_client.get_json.return_value = {"metadata": {}, "info": {}}

    result = get_match(client=mock_client, region=Region.KR, match_id="KR_12345")

    assert result == {"metadata": {}, "info": {}}
    mock_client.get_json.assert_called_once()
    # KR regional host is asia
    assert "asia.api" in mock_client.get_json.call_args[1]["url"]
    assert "matches/KR_12345" in mock_client.get_json.call_args[1]["url"]
