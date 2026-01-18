from unittest.mock import MagicMock

from app.domain.enums import Division, QueueType, Region, Tier
from app.riot_accessor.endpoints.league_v4 import list_league_entries


def test_list_league_entries():
    mock_client = MagicMock()
    mock_client.get_json.return_value = [{"summonerName": "test"}]

    result = list_league_entries(
        client=mock_client,
        region=Region.NA,
        queue=QueueType.RANKED_SOLO_5x5,
        tier=Tier.GOLD,
        division=Division.IV,
    )

    assert result == [{"summonerName": "test"}]
    # Verify URL construction uses Enum values, not names if they differ (though here they default to same)
    # The important part is that the function accepted Enums.
    mock_client.get_json.assert_called_once()
    call_kwargs = mock_client.get_json.call_args[1]
    assert "entries/RANKED_SOLO_5x5/GOLD/IV" in call_kwargs["url"]
