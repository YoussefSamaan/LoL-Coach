from __future__ import annotations

import shutil
from pathlib import Path

from ingest.pipeline import PipelineStep, PipelineContext
from core.logging import get_logger

logger = get_logger(__name__)


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
