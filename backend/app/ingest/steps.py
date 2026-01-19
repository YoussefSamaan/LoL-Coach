from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime

from app.config.settings import settings
from app.domain.enums import Region, QueueType, Tier, Division
from app.ingest.pipeline import PipelineStep, PipelineContext
from app.ingest.crawler import RiotCrawler
from app.ingest.processor import MatchProcessor
from app.ingest.ddragon import DataDragonClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Helper to get today's date string
def get_date_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


class FetchStaticDataStep(PipelineStep):
    """
    Ensures auxiliary data exists.
    """

    name = "Static Data"

    def run(self, context: PipelineContext) -> None:
        # Check if we should fetch/update the map
        if settings.ingest.should_fetch_champion_map:
            client = DataDragonClient()
            if not settings.champion_map_path.exists():
                settings.champion_map_path.parent.mkdir(parents=True, exist_ok=True)

            client.save_champion_map(settings.champion_map_path)
            logger.info(f"Saved static data to {settings.champion_map_path.name}")
        else:
            if not settings.champion_map_path.exists():
                logger.warning("Champion map disabled but file missing. Names will be IDs.")

        context.state["champion_map_path"] = settings.champion_map_path


class ScanLadderStep(PipelineStep):
    name = "Scan Ladder"

    def run(self, context: PipelineContext) -> None:
        crawler = RiotCrawler()
        all_puuids = []
        defaults = settings.ingest.defaults

        for src in settings.ingest.sources:
            if src.get("type") == "ladder":
                reg = Region[src.get("region", defaults.get("region", "NA"))]
                q = QueueType[src.get("queue", defaults.get("queue", "RANKED_SOLO_5x5"))]
                t = Tier[src.get("tier", "CHALLENGER")]
                d = Division[src.get("division", "I")]
                count = src.get("count", 5)

                logger.info(f"Scanning {reg.value} {t.value} {d.value}...")
                pids = crawler.fetch_ladder_puuids(reg, q, t, d, count)
                all_puuids.extend(pids)

        context.state["puuids"] = list(set(all_puuids))
        logger.info(f"Found {len(context.state['puuids'])} unique players.")


class ScanHistoryStep(PipelineStep):
    name = "Scan Histories"

    def run(self, context: PipelineContext) -> None:
        puuids = context.state.get("puuids", [])
        if not puuids:
            return

        crawler = RiotCrawler()
        reg_str = settings.ingest.defaults.get("region", "NA")
        reg = Region[reg_str]
        count = settings.ingest.defaults.get("matches_per_player", 2)
        min_time = context.state.get("min_match_time", 0)

        mids = crawler.scan_match_history(reg, puuids, count, start_time=min_time)
        context.state["match_ids"] = mids
        logger.info(f"Found {len(mids)} unique matches.")


class DownloadContentStep(PipelineStep):
    name = "Download Content"

    def run(self, context: PipelineContext) -> None:
        mids = context.state.get("match_ids", set())
        if not mids:
            return

        out_dir = context.base_dir / settings.ingest.paths.raw_dir
        min_time = context.state.get("min_match_time", 0)

        crawler = RiotCrawler()
        crawler.download_matches(mids, out_dir, min_time=min_time)

        context.state["raw_dir"] = out_dir


class ProcessDataStep(PipelineStep):
    """
    Parses Raw JSONs.
    Saves to: configured processed directory and filename
    """

    name = "Process Data"

    def run(self, context: PipelineContext) -> None:
        raw_dir = context.state.get("raw_dir")
        if not raw_dir:
            return

        fmt = settings.ingest.paths.processed_file_type

        # Use centralized property
        out_file = settings.processed_file_path
        out_file.parent.mkdir(parents=True, exist_ok=True)

        map_path = context.state.get("champion_map_path", settings.champion_map_path)
        min_time = context.state.get("min_match_time", 0)

        processor = MatchProcessor(map_path)
        processor.process_dir(raw_dir, out_file, min_time=min_time, fmt=fmt)

        context.state["processed_file"] = out_file


class CleanupStep(PipelineStep):
    name = "Cleanup"

    def __init__(self, target_key: str):
        self.target_key = target_key

    def run(self, context: PipelineContext) -> None:
        path = context.state.get(self.target_key)
        if isinstance(path, Path) and path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            logger.info(f"Deleted {path}")
