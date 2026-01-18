from __future__ import annotations

from urllib.parse import quote

from app.domain.enums import Division, QueueType, Region, Tier
from app.riot_accessor.http import RiotHttpClient
from app.riot_accessor.routing import platform_host


def list_league_entries(
    *,
    client: RiotHttpClient,
    region: Region,
    queue: QueueType,
    tier: Tier,
    division: Division,
    page: int = 1,
) -> list[dict]:
    """
    League-v4 rank bucket listing.

    Example:
      queue=RANKED_SOLO_5x5, tier=GOLD, division=IV, page=1
    """
    host = platform_host(region)
    path = f"/lol/league/v4/entries/{quote(queue.value, safe='')}/{quote(tier.value, safe='')}/{quote(division.value, safe='')}"
    return list(client.get_json(url=f"{host}{path}", params={"page": page}))
