from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.riot_accessor.client import RiotClient
from app.domain.enums import Region


def get_summoner_by_id(client: RiotClient, region: Region, summoner_id: str) -> dict[str, Any]:
    """
    /lol/summoner/v4/summoners/{encryptedSummonerId}
    """
    url = f"https://{region.value}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"
    return client.get_json(url=url)
