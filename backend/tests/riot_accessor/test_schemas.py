from app.domain.enums import Division, QueueType, Tier
from app.riot_accessor.schemas import LeagueEntry


def test_league_entry_schema_valid():
    entry = LeagueEntry(
        puuid="test-puuid",
        summonerName="TestName",
        queueType=QueueType.RANKED_SOLO_5x5,
        tier=Tier.GOLD,
        rank=Division.IV,
        leaguePoints=100,
        wins=10,
        losses=5,
    )

    assert entry.queueType == QueueType.RANKED_SOLO_5x5
    assert entry.tier == Tier.GOLD
    assert entry.rank == Division.IV
    assert entry.wins == 10


def test_league_entry_schema_serialization():
    data = {
        "puuid": "test-puuid",
        "queueType": "RANKED_SOLO_5x5",
        "tier": "CHALLENGER",
        "rank": "I",  # Apex tiers usually always return "I"
        "wins": 50,
    }

    entry = LeagueEntry.model_validate(data)
    assert entry.queueType == QueueType.RANKED_SOLO_5x5
    assert entry.tier == Tier.CHALLENGER
    assert entry.rank == Division.I
