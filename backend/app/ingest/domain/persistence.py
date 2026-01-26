from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from app.utils.logger import get_logger
from app.ingest.domain.parser import parse_match_row

logger = get_logger(__name__)


def batch_process_raw_matches(
    input_dir: Path,
    output_root: Path,
    id_map: dict,
    rank_map: dict,
    min_time: int = 0,
    output_format: str = "parquet",
) -> None:
    """
    Reads JSONs (recursively) from input_dir, parses them, and saves partitioned datasets.

    Args:
        input_dir: Directory containing raw Riot API JSON files (raw/Region/Tier/Div/Date/ID.json).
        output_root: Directory to save parsed files (parsed/Region/Tier/Div/Date.json).
        id_map: Champion ID to Name map.
        rank_map: Map of MatchID -> {tier, division, region}.
        min_time: Filter out matches older than this timestamp.
        output_format: 'json' or 'parquet'. (Currently implements JSON output logic).

    Partitioning Strategy:
        Region / Tier / Division / Day -> stored as one JSON file per day.

    Example:
        raw/NA/CHALLENGER/I/2024-01-01/123.json
        -> parsed/NA/CHALLENGER/I/2024-01-01.json
    """
    # Find all JSONs recursively
    files = list(input_dir.glob("**/*.json"))
    logger.info(f"Processing {len(files)} matches from {input_dir.name}...")

    rows_buffer = []

    for f in files:
        try:
            raw = json.loads(f.read_text())

            # Pre-check time if possible (optimization)
            creation = raw.get("info", {}).get("gameCreation", 0) // 1000
            if min_time > 0 and creation < min_time:
                continue

            # Resolve rank context
            match_id = raw.get("metadata", {}).get("matchId")
            ctx = rank_map.get(match_id, {})

            # If context is missing (fresh run without scan), try to infer from path
            # Structure: .../raw/REGION/TIER/DIV/DATE/MATCH_ID.json
            if not ctx.get("region") or not ctx.get("tier"):
                try:
                    rel_path = f.relative_to(input_dir)
                    # We expect at least 4 parts: Region, Tier, Div, Date, Filename
                    if len(rel_path.parts) >= 4:
                        ctx = {
                            "region": rel_path.parts[0],
                            "tier": rel_path.parts[1],
                            "division": rel_path.parts[2],
                        }
                except Exception:
                    pass

            new_row = parse_match_row(raw, id_map, ctx)

            if new_row:
                # Inject region if missing
                new_row["region"] = ctx.get("region", "NA")
                rows_buffer.append(new_row)
        except Exception as e:
            logger.warning(f"Failed to process raw match {f}: {e}")

    if not rows_buffer:
        logger.warning("No valid match entries found.")
        return

    df = pd.DataFrame(rows_buffer)

    # Save Parsed Rows
    try:
        # Group by Region, Tier, Division, and Date (YYYY-MM-DD)
        for (region, tier, division, day), group in df.groupby(
            ["region", "tier", "division", "day"]
        ):
            target_dir = output_root / str(region) / str(tier) / str(division)
            target_dir.mkdir(parents=True, exist_ok=True)

            target_file = target_dir / f"{day}.json"

            records = group.to_dict(orient="records")

            final_records = []
            existing_ids = set()

            if target_file.exists():
                try:
                    existing = json.loads(target_file.read_text())
                    if isinstance(existing, list):
                        final_records = existing
                        existing_ids = {r.get("match_id") for r in existing}
                except Exception:
                    pass

            # Filter duplicates
            new_records = [r for r in records if r.get("match_id") not in existing_ids]

            if new_records:
                final_records.extend(new_records)
                target_file.write_text(json.dumps(final_records, indent=2))
                logger.info(f"Appended {len(new_records)} new matches to {target_file.name}")
            else:
                logger.info(f"No new matches for {target_file.name} (skipped duplicates)")

        logger.info(f"Saved {len(df)} matches to JSON partitions in {output_root}")

    except Exception as e:
        logger.error(f"Failed to save partitioned JSON: {e}")
