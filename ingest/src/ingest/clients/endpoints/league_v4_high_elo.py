from __future__ import annotations

from core.domain.enums import QueueType, Region
from ingest.clients.http import RiotHttpClient
from ingest.clients.routing import platform_host


def get_challenger_league(
    *,
    client: RiotHttpClient,
    region: Region,
    queue: QueueType = QueueType.RANKED_SOLO_5x5,
) -> dict:
    host = platform_host(region)
    path = f"/lol/league/v4/challengerleagues/by-queue/{queue.value}"
    # Returns a LeagueListDTO containing 'entries' (list of Summoners)
    return client.get_json(url=f"{host}{path}")


def get_grandmaster_league(
    *,
    client: RiotHttpClient,
    region: Region,
    queue: QueueType = QueueType.RANKED_SOLO_5x5,
) -> dict:
    host = platform_host(region)
    path = f"/lol/league/v4/grandmasterleagues/by-queue/{queue.value}"
    return client.get_json(url=f"{host}{path}")


def get_master_league(
    *,
    client: RiotHttpClient,
    region: Region,
    queue: QueueType = QueueType.RANKED_SOLO_5x5,
) -> dict:
    host = platform_host(region)
    path = f"/lol/league/v4/masterleagues/by-queue/{queue.value}"
    return client.get_json(url=f"{host}{path}")
