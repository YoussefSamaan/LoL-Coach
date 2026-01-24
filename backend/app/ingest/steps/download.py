from __future__ import annotations

import json
from datetime import datetime, timezone

from app.config.settings import settings
from app.ingest.pipeline import PipelineStep, PipelineContext
from app.ingest.clients.crawler import RiotCrawler
from app.domain.enums import Region
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DownloadContentStep(PipelineStep):
    """
    Downloads matches to: raw/{Region}/{Tier}/{Division}/{Date}/{MatchID}.json
    """

    name = "Download Content"

    def run(self, context: PipelineContext) -> None:
        match_ids = context.state.get("match_ids", set())
        if not match_ids:
            return

        base_raw_dir = context.base_dir / settings.ingest.paths.raw_dir
        min_time = context.state.get("min_match_time", 0)
        match_rank_map = context.state.get("match_rank_map", {})

        crawler = RiotCrawler()

        # We iterate here to enforce specific directory hierarchy.

        logger.info(f"Downloading {len(match_ids)} matches...")
        valid_files = []

        for match_id in match_ids:
            ctx = match_rank_map.get(match_id, {})
            region = ctx.get("region", "UNKNOWN")
            tier = ctx.get("tier", "UNKNOWN")
            div = ctx.get("division", "IV")

            # Determine date from game creation time.

            # Fetch first
            try:
                data = crawler.get_match(match_id, region if region != "UNKNOWN" else Region.NA)
                if not data:
                    continue

                # Extract Real Date
                info = data.get("info", {})
                game_creation = info.get("gameCreation", 0)
                date_str = datetime.fromtimestamp(game_creation // 1000, tz=timezone.utc).strftime(
                    "%Y-%m-%d"
                )

                if min_time > 0 and (game_creation // 1000) < min_time:
                    continue

                # Target Path
                target_dir = base_raw_dir / region / tier / div / date_str
                target_dir.mkdir(parents=True, exist_ok=True)

                f_path = target_dir / f"{match_id}.json"
                f_path.write_text(json.dumps(data, indent=None))
                valid_files.append(f_path)

            except Exception as e:
                logger.warning(f"Failed to dl {match_id}: {e}")

        # Update raw_dir state (it's now a root, not a single folder of files)
        context.state["raw_dir"] = base_raw_dir
