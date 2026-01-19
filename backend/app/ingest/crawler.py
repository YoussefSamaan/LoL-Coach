from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
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
                # In a real implementation we would pass start_time to client method if supported
                ids = self.client.match_ids_by_puuid(region=region, puuid=pid, count=count)
                match_ids.update(ids)
            except Exception:
                continue
        return match_ids

    def download_matches(self, match_ids: set[str], output_dir: Path, min_time: int = 0) -> None:
        """
        Downloads matches.
        Renames file to: {MATCH_ID}_{TIMESTAMP}.json
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        r_map = {"NA1": Region.NA, "EUW1": Region.EUW, "KR": Region.KR}

        for mid in match_ids:
            prefix = mid.split("_")[0].upper()
            reg = r_map.get(prefix, Region.NA)

            # Optimization: Check if we already have this match ID downloaded (ignoring date suffix)
            if list(output_dir.glob(f"{mid}_*.json")):
                continue

            try:
                # 1. Download Match Data
                data = self.client.match(region=reg, match_id=mid)

                # 2. Extract Timestamp (ms -> s)
                creation_ms = data.get("info", {}).get("gameCreation", 0)
                creation_sec = creation_ms // 1000

                # 3. Filter if too old
                if min_time > 0 and creation_sec < min_time:
                    continue

                # 4. Construct Filename: MATCHID_YYYY-MM-DD.json
                # Using date string as requested for easier human filtering
                date_str = datetime.fromtimestamp(creation_sec).strftime("%Y-%m-%d")

                # e.g. NA1_12345_2024-01-01.json
                # This makes it very easy to glob filter "NA1_12345_*" or "*_2024-01-01.json"
                filename = f"{mid}_{date_str}.json"
                dest = output_dir / filename

                dest.write_text(json.dumps(data))

            except Exception:
                logger.warning(f"Failed {mid}", exc_info=True)
