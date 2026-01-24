from __future__ import annotations

import json
import pandas as pd

from app.config.settings import settings
from app.ingest.pipeline import PipelineStep, PipelineContext
from app.ingest.domain.aggregator import compute_aggregates
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AggregateStatsStep(PipelineStep):
    """
    Step 3: Aggregate 'Clean Matches' into Daily Grids (JSON).
    Explodes the match data into N*N stats: Role, Synergy, Counter.

    Example Input:
        CleanMatch(blue=[Aatrox(Top), ...], red=[Darius(Top), ...], winner=Blue)

    Example Output:
        stats["Aatrox"]["wins"] += 1
        stats["Aatrox"]["counter"]["Darius"]["wins"] += 1
    """

    name = "Aggregate Stats"

    def run(self, context: PipelineContext) -> None:
        parsed_dir = context.state.get("parsed_dir")
        if not parsed_dir:
            # Try loading default
            parsed_dir = settings.parsed_root
        logger.info(f"Aggregating stats from {parsed_dir}...")

        try:
            # Recursive load of JSONs into one DF
            files = list(parsed_dir.glob("**/*.json"))
            if not files:
                logger.warning("No parsed data found to aggregate.")
                return

            all_data = []
            for f in files:
                try:
                    data = json.loads(f.read_text())
                    if isinstance(data, list):
                        all_data.extend(data)
                except Exception as e:
                    logger.warning(f"Failed to load parsed file {f}: {e}")

            if not all_data:
                return

            df = pd.DataFrame(all_data)
        except Exception as e:
            logger.warning(f"Failed to load parsed data: {e}")
            return

        aggregates_dir = settings.aggregates_root

        # Ensure required columns exist
        required_cols = ["region", "tier", "division", "day"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = "UNKNOWN"

        for (region, tier, division, day_str), group_df in df.groupby(required_cols):
            try:
                stats = compute_aggregates(group_df)

                # Save: aggregates/Region/Tier/Division/Date.json
                day_file = (
                    aggregates_dir / str(region) / str(tier) / str(division) / f"{day_str}.json"
                )
                day_file.parent.mkdir(parents=True, exist_ok=True)

                grid = {
                    "date": day_str,
                    "region": region,
                    "tier": tier,
                    "division": division,
                    "metrics": ["wins", "games"],
                    "stats": stats,
                }

                day_file.write_text(json.dumps(grid, indent=None))
                logger.info(f"Saved aggregation for {day_str}")
            except Exception as e:
                logger.error(f"Failed agg for {day_str}: {e}")
