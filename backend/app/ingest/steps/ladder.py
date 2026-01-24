from __future__ import annotations

from app.config.settings import settings
from app.ingest.pipeline import PipelineStep, PipelineContext
from app.ingest.clients.crawler import RiotCrawler
from app.domain.enums import Region, QueueType, Tier, Division
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ScanLadderStep(PipelineStep):
    """
    Scans the ladder and returns a list of Player Config objects
    (puuid, tier, division) instead of just a flat list of strings.
    """

    name = "Scan Ladder"

    def run(self, context: PipelineContext) -> None:
        crawler = RiotCrawler()
        all_players = []  # List of {"puuid": str, "tier": str, "division": str}
        ingest_defaults = settings.ingest.defaults

        for src in settings.ingest.sources:
            if src.get("type") == "ladder":
                region = Region[src.get("region", ingest_defaults.get("region", "NA"))]
                queue = QueueType[src.get("queue", ingest_defaults.get("queue", "RANKED_SOLO_5x5"))]
                tier = Tier[src.get("tier", "CHALLENGER")]
                division = Division[src.get("division", "I")]
                count = src.get("count", 5)

                logger.info(f"Scanning {region.value} {tier.value} {division.value}...")
                puuids = crawler.fetch_ladder_puuids(region, queue, tier, division, count)

                for puuid in puuids:
                    all_players.append(
                        {"puuid": puuid, "tier": tier.value, "division": division.value}
                    )

        context.state["players"] = all_players
        logger.info(f"Found {len(all_players)} players.")
