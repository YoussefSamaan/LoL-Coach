import pytest
from unittest.mock import patch, MagicMock
from app.ingest.clients.crawler import RiotCrawler
from app.domain.enums import Region, QueueType, Tier, Division


@pytest.fixture
def mock_riot_client():
    with patch("app.ingest.clients.crawler.RiotClient") as MockClient:
        yield MockClient.from_env.return_value


@pytest.fixture
def crawler(mock_riot_client):
    return RiotCrawler()


def test_fetch_ladder_puuids(crawler, mock_riot_client):
    # Mock entries
    e1 = MagicMock()
    e1.puuid = "p1"
    e1.summonerId = None

    e2 = MagicMock()
    e2.puuid = None
    e2.summonerId = "s2"

    mock_riot_client.league_entries_by_rank.return_value = [e1, e2]

    # Mock summoner lookup for e2
    s2_obj = MagicMock()
    s2_obj.puuid = "p2"
    mock_riot_client.get_summoner.return_value = s2_obj

    puuids = crawler.fetch_ladder_puuids(
        Region.NA, QueueType.RANKED_SOLO_5x5, Tier.CHALLENGER, Division.I, 5
    )

    assert "p1" in puuids
    assert "p2" in puuids
    assert len(puuids) == 2


def test_fetch_ladder_puuids_exception_handling(crawler, mock_riot_client):
    # e2 fails lookup
    e1 = MagicMock()
    e1.puuid = None
    e1.summonerId = "s1"

    mock_riot_client.league_entries_by_rank.return_value = [e1]
    mock_riot_client.get_summoner.side_effect = Exception("API Fail")

    puuids = crawler.fetch_ladder_puuids(
        Region.NA, QueueType.RANKED_SOLO_5x5, Tier.CHALLENGER, Division.I, 5
    )
    assert len(puuids) == 0


def test_scan_match_history(crawler, mock_riot_client):
    mock_riot_client.match_ids_by_puuid.return_value = ["m1", "m2"]

    ids = crawler.scan_match_history(Region.NA, ["p1"], 10)
    assert "m1" in ids
    assert "m2" in ids


def test_scan_match_history_exception(crawler, mock_riot_client):
    mock_riot_client.match_ids_by_puuid.side_effect = Exception("Fail")

    ids = crawler.scan_match_history(Region.NA, ["p1"], 10)
    assert len(ids) == 0


def test_get_match_success(crawler, mock_riot_client):
    mock_riot_client.match.return_value = {"metadata": {}}

    # ID with prefix
    res = crawler.get_match("NA1_123")
    assert res is not None
    # Verify inferred region is NA
    mock_riot_client.match.assert_called_with(region=Region.NA, match_id="NA1_123")

    # ID with different prefix
    crawler.get_match("EUW1_456")
    mock_riot_client.match.assert_called_with(region=Region.EUW, match_id="EUW1_456")


def test_get_match_default_region(crawler, mock_riot_client):
    # ID with unknown prefix
    crawler.get_match("UNKNOWN_123", default_region=Region.KR)
    mock_riot_client.match.assert_called_with(region=Region.KR, match_id="UNKNOWN_123")


def test_get_match_failure(crawler, mock_riot_client):
    mock_riot_client.match.side_effect = Exception("Boom")
    res = crawler.get_match("NA1_123")
    assert res is None
