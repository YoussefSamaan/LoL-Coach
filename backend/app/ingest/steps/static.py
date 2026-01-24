from __future__ import annotations

from app.config.settings import settings
from app.ingest.pipeline import PipelineStep, PipelineContext
from app.ingest.clients.ddragon import DataDragonClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


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
