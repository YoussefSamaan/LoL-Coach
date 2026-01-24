from __future__ import annotations

from app.riot_accessor.client import RiotClient
from app.domain.enums import Region, QueueType, Tier, Division
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RiotCrawler:
    """
    Handles interactions with Riot API for data discovery and downloading.
    """

    def __init__(self):
        self.client = RiotClient.from_env()

    def fetch_ladder_puuids(
        self, region: Region, queue: QueueType, tier: Tier, division: Division, count: int
    ) -> list[str]:
        puuids = []
        entries = self.client.league_entries_by_rank(
            region=region, queue=queue, tier=tier, division=division
        )
        for entry in entries[:count]:
            if entry.puuid:
                puuids.append(entry.puuid)
            elif entry.summonerId:
                try:
                    s = self.client.get_summoner(region=region, summoner_id=entry.summonerId)
                    puuids.append(s.puuid)
                except Exception:
                    continue
        return puuids

    def scan_match_history(
        self, region: Region, puuids: list[str], count: int, start_time: int = 0
    ) -> set[str]:
        """
        Scans match history.
        """
        match_ids = set()
        for pid in puuids:
            try:
                # TODO: Pass 'start_time' to the client method once supported.
                # Riot's endpoint `/lol/match/v5/matches/by-puuid/{puuid}/ids` supports a `startTime`
                # query parameter (epoch seconds). Using this would allow us to efficiently fetch ONLY
                # matches from a specific timeframe (e.g., "yesterday onwards") instead of fetching
                # the last N matches and filtering them manually, saving API calls and bandwidth.
                ids = self.client.match_ids_by_puuid(region=region, puuid=pid, count=count)
                match_ids.update(ids)
            except Exception as e:
                logger.warning(f"Failed to scan history for {pid}: {e}")
                continue
        return match_ids

    def get_match(self, match_id: str, default_region: Region = Region.NA) -> dict | None:
        """
        Fetch single match data. Resolves region from ID prefix if possible.
        """
        r_map = {"NA1": Region.NA, "EUW1": Region.EUW, "KR": Region.KR}

        # match_id looks like NA1_1234567890
        prefix = match_id.split("_")[0].upper()
        reg = r_map.get(prefix, default_region)

        try:
            return self.client.match(region=reg, match_id=match_id)
        except Exception as e:
            logger.warning(f"Failed to fetch match {match_id}: {e}")
            return None
