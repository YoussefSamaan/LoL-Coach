from __future__ import annotations

import argparse
from app.utils.logger import get_logger

from app.config.settings import settings
from app.ingest.pipeline import IngestPipeline, PipelineContext
from app.ingest.steps import (
    FetchStaticDataStep,
    ScanLadderStep,
    ScanHistoryStep,
    DownloadContentStep,
    ParseMatchStep,
    AggregateStatsStep,
    CleanupStep,
)

logger = get_logger("IngestMain")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Ingestion Pipeline.\n"
            "NOTE: Please update 'backend/app/config/definitions/ingest.yaml' "
            "to configure sources, regions, and file paths before running."
        )
    )
    parser.add_argument(
        "--cleanup-raw", action="store_true", help="Delete raw JSONs after processing"
    )
    parser.add_argument(
        "--since", type=int, help="Filter matches after this Unix timestamp", default=0
    )
    parser.add_argument(
        "--format",
        choices=["parquet", "csv"],
        default="parquet",
        help="Output format for processed data",
    )
    parser.add_argument("--note", help="Optional run note", default="")
    args = parser.parse_args()

    # Base dir: backend/data
    base_dir = settings.data_root

    run_id = f"manual_{args.note}" if args.note else "manual"

    context = PipelineContext(run_id=run_id, base_dir=base_dir)
    context.state["min_match_time"] = args.since
    context.state["output_format"] = args.format

    pipeline = IngestPipeline()

    pipeline.add_step(FetchStaticDataStep())
    pipeline.add_step(ScanLadderStep())
    pipeline.add_step(ScanHistoryStep())
    pipeline.add_step(DownloadContentStep())
    pipeline.add_step(ParseMatchStep())
    pipeline.add_step(AggregateStatsStep())

    if args.cleanup_raw:
        pipeline.add_step(CleanupStep(target_key="raw_dir"))

    try:
        pipeline.execute(context)
        return 0
    except Exception:
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
