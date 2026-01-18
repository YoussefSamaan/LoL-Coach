from unittest.mock import patch

import pytest
from app.domain.enums import Division, QueueType, Region, Tier
from app.riot_accessor.client import RiotClient


@pytest.fixture
def client():
    return RiotClient(api_key="test-key")


def test_league_entries_by_rank_standard(client):
    with patch("app.riot_accessor.client.list_league_entries") as mock_list:
        mock_list.return_value = [
            {
                "optimizer": None,
                "leaguePoints": 100,
                "losses": 10,
                "summonerName": "TestSummoner",
                "wins": 20,
                "tier": "GOLD",
                "queueType": "RANKED_SOLO_5x5",
                "rank": "IV",
                "summonerId": "test-id",
                "hotStreak": False,
                "veteran": False,
                "freshBlood": False,
                "inactive": False,
                # puuid might be missing in older responses, handled by schema
            }
        ]

        results = client.league_entries_by_rank(
            region=Region.NA, queue=QueueType.RANKED_SOLO_5x5, tier=Tier.GOLD, division=Division.IV
        )

        assert len(results) == 1
        assert results[0].summonerName == "TestSummoner"
        assert results[0].tier == Tier.GOLD
        assert results[0].queueType == QueueType.RANKED_SOLO_5x5

        mock_list.assert_called_once_with(
            client=client,
            region=Region.NA,
            queue=QueueType.RANKED_SOLO_5x5,
            tier=Tier.GOLD,
            division=Division.IV,
            page=1,
        )


def test_league_entries_by_rank_apex(client):
    # Function under test
    import app.riot_accessor.client as client_mod

    with patch.object(client_mod, "get_challenger_league") as mock_challenger:
        mock_challenger.return_value = {
            "Entries": [
                {
                    "summonerName": "TopPlayer",
                    "leaguePoints": 1000,
                    "wins": 100,
                    "losses": 50,
                    "tier": "CHALLENGER",
                    "queueType": "RANKED_SOLO_5x5",
                    "rank": "I",
                    "summonerId": "top-id",
                }
            ]
        }

        results = client.league_entries_by_rank(
            region=Region.KR, queue=QueueType.RANKED_SOLO_5x5, tier=Tier.CHALLENGER
        )

        # Verify call happened
        mock_challenger.assert_called_once()

        assert len(results) == 1
        assert results[0].tier == Tier.CHALLENGER
        assert results[0].summonerName == "TopPlayer"


def test_league_entries_by_rank_grandmaster(client):
    import app.riot_accessor.client as client_mod

    with patch.object(client_mod, "get_grandmaster_league") as mock_gm:
        mock_gm.return_value = {"Entries": [{"summonerName": "GMPlayer", "tier": "GRANDMASTER"}]}

        results = client.league_entries_by_rank(
            region=Region.EUW, queue=QueueType.RANKED_SOLO_5x5, tier=Tier.GRANDMASTER
        )

        mock_gm.assert_called_once()
        assert len(results) == 1
        assert results[0].tier == Tier.GRANDMASTER


def test_league_entries_by_rank_master(client):
    import app.riot_accessor.client as client_mod

    with patch.object(client_mod, "get_master_league") as mock_master:
        mock_master.return_value = {
            # Note: client code lower-cases it now, checking normalization
            "Entries": [{"summonerName": "MasterPlayer", "tier": "MASTER"}]
        }

        results = client.league_entries_by_rank(
            region=Region.EUW, queue=QueueType.RANKED_SOLO_5x5, tier=Tier.MASTER
        )

        mock_master.assert_called_once()
        assert len(results) == 1
        assert results[0].tier == Tier.MASTER


def test_league_entries_by_rank_default_division(client):
    with patch("app.riot_accessor.client.list_league_entries") as mock_list:
        mock_list.return_value = []

        client.league_entries_by_rank(
            region=Region.NA,
            queue=QueueType.RANKED_SOLO_5x5,
            tier=Tier.GOLD,
            # Division not provided, should default to I
        )

        args = mock_list.call_args[1]
        assert args["division"] == Division.I


def test_client_match_methods(client):
    with (
        patch("app.riot_accessor.client.get_match") as mock_get_match,
        patch("app.riot_accessor.client.list_match_ids_by_puuid") as mock_list_match,
    ):
        mock_get_match.return_value = {"id": "m1"}
        mock_list_match.return_value = ["m1"]

        client.match(region=Region.NA, match_id="m1")
        mock_get_match.assert_called_once()

        client.match_ids_by_puuid(region=Region.NA, puuid="p1")
        mock_list_match.assert_called_once()
