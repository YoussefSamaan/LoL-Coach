from __future__ import annotations

from urllib.parse import quote

from app.domain.enums import Region
from app.riot_accessor.http import RiotHttpClient
from app.riot_accessor.routing import regional_host


def list_match_ids_by_puuid(
    *, client: RiotHttpClient, region: Region, puuid: str, count: int = 20
) -> list[str]:
    host = regional_host(region)
    path = f"/lol/match/v5/matches/by-puuid/{quote(puuid, safe='')}/ids"
    return list(client.get_json(url=f"{host}{path}", params={"count": count}))


def get_match(*, client: RiotHttpClient, region: Region, match_id: str) -> dict:
    host = regional_host(region)
    path = f"/lol/match/v5/matches/{quote(match_id, safe='')}"
    return client.get_json(url=f"{host}{path}")
