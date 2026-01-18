from unittest.mock import MagicMock

from app.domain.enums import QueueType, Region
from app.riot_accessor.endpoints.league_v4_high_elo import (
    get_challenger_league,
    get_grandmaster_league,
    get_master_league,
)


def test_get_challenger_league():
    mock_client = MagicMock()
    mock_client.get_json.return_value = {"entries": []}

    result = get_challenger_league(
        client=mock_client, region=Region.KR, queue=QueueType.RANKED_SOLO_5x5
    )

    assert result == {"entries": []}
    mock_client.get_json.assert_called_once()
    call_kwargs = mock_client.get_json.call_args[1]
    assert "challengerleagues/by-queue/RANKED_SOLO_5x5" in call_kwargs["url"]
    assert "kr.api" in call_kwargs["url"]


def test_get_grandmaster_league():
    mock_client = MagicMock()
    mock_client.get_json.return_value = {"entries": []}

    get_grandmaster_league(client=mock_client, region=Region.EUW, queue=QueueType.RANKED_SOLO_5x5)

    mock_client.get_json.assert_called_once()
    assert "grandmasterleagues/by-queue/RANKED_SOLO_5x5" in mock_client.get_json.call_args[1]["url"]


def test_get_master_league():
    mock_client = MagicMock()
    mock_client.get_json.return_value = {"entries": []}

    get_master_league(client=mock_client, region=Region.NA, queue=QueueType.RANKED_SOLO_5x5)

    mock_client.get_json.assert_called_once()
    assert "masterleagues/by-queue/RANKED_SOLO_5x5" in mock_client.get_json.call_args[1]["url"]
