from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineContext:
    """
    Shared state for the pipeline run.
    """

    run_id: str
    base_dir: Path

    # Key-value store for passing data between steps
    state: Dict[str, Any] = field(default_factory=dict)

    @property
    def check_state(self):
        return self.state.keys()


class PipelineStep:
    """
    Unit of work in the pipeline.
    """

    name: str = "BaseStep"

    def run(self, context: PipelineContext) -> None:
        raise NotImplementedError


class IngestPipeline:
    """
    Configurable pipeline orchestrator.
    """

    def __init__(self) -> None:
        self.steps: List[PipelineStep] = []

    def add_step(self, step: PipelineStep) -> "IngestPipeline":
        self.steps.append(step)
        return self

    def remove_step_by_name(self, name: str) -> "IngestPipeline":
        self.steps = [s for s in self.steps if s.name != name]
        return self

    def execute(self, context: PipelineContext) -> None:
        logger.info(f"=== Pipeline Start: {context.run_id} ===")
        context.base_dir.mkdir(parents=True, exist_ok=True)

        for step in self.steps:
            logger.info(f">> Step: {step.name}")
            try:
                step.run(context)
            except Exception as e:
                logger.error(f"!! Failed at {step.name}: {e}")
                raise e

        logger.info("=== Pipeline Complete ===")
