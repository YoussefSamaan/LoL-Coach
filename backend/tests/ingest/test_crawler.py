import json
from unittest.mock import MagicMock, patch
import pytest

from app.ingest.crawler import RiotCrawler
from app.domain.enums import Region, QueueType, Tier, Division


@pytest.fixture
def mock_client():
    with patch("app.ingest.crawler.RiotClient") as MockClient:
        client_instance = MockClient.from_env.return_value
        yield client_instance


def test_fetch_ladder_puuids(mock_client):
    crawler = RiotCrawler()

    # Mock entries
    e1 = MagicMock(puuid="p1", summonerId=None)
    e2 = MagicMock(puuid=None, summonerId="s2")  # Needs lookup

    mock_client.league_entries_by_rank.return_value = [e1, e2]

    # Mock summoner lookup
    s2_obj = MagicMock(puuid="p2")
    mock_client.get_summoner.return_value = s2_obj

    puuids = crawler.fetch_ladder_puuids(
        Region.NA, QueueType.RANKED_SOLO_5x5, Tier.CHALLENGER, Division.I, 2
    )

    assert "p1" in puuids
    assert "p2" in puuids
    mock_client.league_entries_by_rank.assert_called_once()
    mock_client.get_summoner.assert_called_with(region=Region.NA, summoner_id="s2")


def test_fetch_ladder_puuids_lookup_fail(mock_client):
    crawler = RiotCrawler()
    e1 = MagicMock(puuid=None, summonerId="s1")
    mock_client.league_entries_by_rank.return_value = [e1]
    mock_client.get_summoner.side_effect = Exception("Not Found")

    puuids = crawler.fetch_ladder_puuids(
        Region.NA, QueueType.RANKED_SOLO_5x5, Tier.CHALLENGER, Division.I, 1
    )

    assert len(puuids) == 0


def test_scan_match_history(mock_client):
    crawler = RiotCrawler()
    mock_client.match_ids_by_puuid.return_value = ["M1", "M2"]

    ids = crawler.scan_match_history(Region.NA, ["p1"], 2)

    assert ids == {"M1", "M2"}
    mock_client.match_ids_by_puuid.assert_called_with(region=Region.NA, puuid="p1", count=2)


def test_download_matches(mock_client, tmp_path):
    crawler = RiotCrawler()
    out_dir = tmp_path / "raw"

    # Match data
    match_data = {
        "metadata": {"matchId": "NA1_100"},
        "info": {"gameCreation": 1700000000000},  # 1700... seconds
    }

    mock_client.match.return_value = match_data

    crawler.download_matches({"NA1_100"}, out_dir, min_time=0)

    # Check file exists
    files = list(out_dir.glob("*.json"))
    assert len(files) == 1
    assert "NA1_100" in files[0].name

    # Check content
    content = json.loads(files[0].read_text())
    assert content["metadata"]["matchId"] == "NA1_100"


def test_download_matches_skip_old(mock_client, tmp_path):
    crawler = RiotCrawler()
    out_dir = tmp_path

    match_data = {
        "info": {"gameCreation": 1000000000000}  # Old time
    }
    mock_client.match.return_value = match_data

    # Set min_time to future
    crawler.download_matches({"NA1_200"}, out_dir, min_time=2000000000)

    files = list(out_dir.glob("*.json"))
    assert len(files) == 0


def test_download_matches_skip_existing(mock_client, tmp_path):
    crawler = RiotCrawler()
    out_dir = tmp_path

    # Use a fixed timestamp and verify check
    match_data = {"metadata": {"matchId": "NA1_300"}, "info": {"gameCreation": 1600000000000}}
    mock_client.match.return_value = match_data

    mid = "NA1_300"

    # Run 1: Should call client and save file
    crawler.download_matches({mid}, out_dir)
    assert mock_client.match.call_count == 1

    # Check if ANY file was created
    saved_files = list(out_dir.glob("*.json"))
    assert len(saved_files) == 1
    print(f"Created file: {saved_files[0]}")

    # Run 2: Should find the file and skip
    crawler.download_matches({mid}, out_dir)
    assert mock_client.match.call_count == 1  # Still 1


def test_scan_match_history_exception(mock_client):
    crawler = RiotCrawler()
    # First call raises, second succeeds
    mock_client.match_ids_by_puuid.side_effect = [Exception("Fail"), ["M1"]]

    ids = crawler.scan_match_history(Region.NA, ["p1", "p2"], 2)

    assert ids == {"M1"}


def test_download_matches_exception(mock_client, tmp_path):
    crawler = RiotCrawler()
    out_dir = tmp_path

    mock_client.match.side_effect = Exception("Fail")

    # Should not raise
    crawler.download_matches({"NA1_500"}, out_dir)
    assert len(list(out_dir.glob("*"))) == 0
