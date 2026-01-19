from unittest.mock import MagicMock
from app.riot_accessor.endpoints.summoner_v4 import get_summoner_by_id
from app.domain.enums import Region


def test_get_summoner_by_id():
    mock_client = MagicMock()
    mock_client.get_json.return_value = {"name": "Test"}

    res = get_summoner_by_id(mock_client, Region.NA, "summ_123")

    assert res == {"name": "Test"}

    mock_client.get_json.assert_called_once_with(
        url="https://NA.api.riotgames.com/lol/summoner/v4/summoners/summ_123"
    )
