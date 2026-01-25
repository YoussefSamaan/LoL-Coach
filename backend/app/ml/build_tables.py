"""ML training pipeline - builds artifacts from parsed match data.

This module processes parsed match data to compute:
- Role-specific champion winrates
- Champion synergy effects (with allies)
- Champion counter effects (against enemies)
- Global baseline winrates

The output is a validated ArtifactBundle saved to the artifacts directory.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import cast

import pandas as pd

from app.config.settings import settings
from app.ml.artifacts import ArtifactBundle, save_artifact_bundle
from app.ml.training import (
    ArtifactStats,
    LiftStat,
    ManifestData,
    SmoothingConfig,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def compute_role_strength(df: pd.DataFrame, config: SmoothingConfig) -> dict[str, dict[str, float]]:
    """Compute role-specific champion winrates with Bayesian smoothing.

    Uses Beta(alpha, beta) prior to smooth winrates, especially for
    low-sample champions.

    Args:
        df: DataFrame with columns [target_role, champ, win].
        config: Smoothing configuration.

    Returns:
        Nested dict: {Role: {Champion: winrate}}
        Example: {"MID": {"Ahri": 0.52, "Zed": 0.51}}
    """
    grouped = df.groupby(["target_role", "champ"])["win"].agg(["sum", "count"])

    # Bayesian smoothing: (wins + alpha) / (games + alpha + beta)
    grouped["winrate"] = (grouped["sum"] + config.role_alpha) / (
        grouped["count"] + config.role_alpha + config.role_beta
    )

    stats: dict[str, dict[str, float]] = {}
    for key, row in grouped.iterrows():
        role, champ = cast(tuple[str, str], key)
        if role not in stats:
            stats[role] = {}
        stats[role][champ] = float(row["winrate"])

    return stats


def compute_synergy(
    df: pd.DataFrame, global_winrates: dict[str, float], config: SmoothingConfig
) -> dict[str, dict[str, LiftStat]]:
    """Compute ally synergy lifts with sample counts.

    For each (champion, ally) pair, computes how much the champion's
    winrate changes when paired with that ally.

    Args:
        df: DataFrame with columns [champ, allies, win].
        global_winrates: Baseline winrates per champion.
        config: Smoothing configuration.

    Returns:
        Nested dict: {Champion: {Ally: LiftStat}}
        Example: {"Ahri": {"Amumu": LiftStat(lift=0.03, count=50)}}
    """
    # Explode allies list to get one row per (champ, ally) pair
    mini_df = df[["champ", "allies", "win"]].copy()
    exploded = mini_df.explode("allies")

    # Remove rows where allies is NaN (no allies)
    exploded = exploded.dropna(subset=["allies"])

    # Group by (champ, ally)
    grouped = exploded.groupby(["champ", "allies"])["win"].agg(["sum", "count"])

    # Apply smoothing
    grouped["pair_winrate"] = (grouped["sum"] + config.pair_alpha) / (
        grouped["count"] + config.pair_alpha + config.pair_beta
    )

    stats: dict[str, dict[str, LiftStat]] = {}

    for key, row in grouped.iterrows():
        champ, ally = cast(tuple[str, str], key)
        count = int(row["count"])

        # Skip pairs with too few samples
        if count < config.min_samples:
            continue

        # Compute lift from baseline
        base = global_winrates.get(champ, 0.5)
        lift = float(row["pair_winrate"] - base)

        # Clamp lift to reasonable range
        lift = max(-1.0, min(1.0, lift))

        if champ not in stats:
            stats[champ] = {}
        stats[champ][ally] = LiftStat(lift=lift, count=count)

    return stats


def compute_counter(
    df: pd.DataFrame, global_winrates: dict[str, float], config: SmoothingConfig
) -> dict[str, dict[str, LiftStat]]:
    """Compute enemy counter lifts with sample counts.

    For each (champion, enemy) pair, computes how much the champion's
    winrate changes when matched against that enemy.

    Args:
        df: DataFrame with columns [champ, enemies, win].
        global_winrates: Baseline winrates per champion.
        config: Smoothing configuration.

    Returns:
        Nested dict: {Champion: {Enemy: LiftStat}}
        Example: {"Ahri": {"Zed": LiftStat(lift=-0.02, count=75)}}
    """
    mini_df = df[["champ", "enemies", "win"]].copy()
    exploded = mini_df.explode("enemies")

    # Remove rows where enemies is NaN
    exploded = exploded.dropna(subset=["enemies"])

    grouped = exploded.groupby(["champ", "enemies"])["win"].agg(["sum", "count"])

    # Apply smoothing
    grouped["matchup_winrate"] = (grouped["sum"] + config.pair_alpha) / (
        grouped["count"] + config.pair_alpha + config.pair_beta
    )

    stats: dict[str, dict[str, LiftStat]] = {}

    for key, row in grouped.iterrows():
        champ, enemy = cast(tuple[str, str], key)
        count = int(row["count"])

        # Skip pairs with too few samples
        if count < config.min_samples:
            continue

        # Compute lift from baseline
        base = global_winrates.get(champ, 0.5)
        lift = float(row["matchup_winrate"] - base)

        # Clamp lift to reasonable range
        lift = max(-1.0, min(1.0, lift))

        if champ not in stats:
            stats[champ] = {}
        stats[champ][enemy] = LiftStat(lift=lift, count=count)

    return stats


def build_tables(config: SmoothingConfig | None = None) -> Path | None:
    """Build ML artifacts from parsed match data.

    Processes all parsed match data to compute role strength, synergy,
    and counter statistics. Saves validated artifacts to the artifacts
    directory.

    Args:
        config: Smoothing configuration. If None, uses defaults.

    Returns:
        Path to the created run directory, or None if failed.

    Example:
        >>> from app.ml.training import SmoothingConfig
        >>> config = SmoothingConfig(min_samples=10)
        >>> run_dir = build_tables(config)
        >>> print(f"Artifacts saved to: {run_dir}")
    """
    if config is None:
        config = SmoothingConfig()

    logger.info("Starting artifact build...")
    logger.info(
        f"Smoothing config: role=Beta({config.role_alpha},{config.role_beta}), "
        f"pair=Beta({config.pair_alpha},{config.pair_beta}), "
        f"min_samples={config.min_samples}"
    )

    parsed_dir = settings.data_root / settings.ingest.paths.parsed_dir

    if not parsed_dir.exists():
        logger.error(f"Parsed data directory not found: {parsed_dir}")
        return None

    # 1. Load Data from JSON files
    try:
        # Find all JSON files recursively
        json_files = list(parsed_dir.glob("**/*.json"))
        if not json_files:
            logger.error(f"No JSON files found in {parsed_dir}")
            return None
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        # Load all JSON files into a single DataFrame
        all_data = []
        for json_file in json_files:
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    all_data.extend(data)
                else:
                    all_data.append(data)
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")
                continue
        
        if not all_data:
            logger.error("No valid data loaded from JSON files")
            return None
        
        df = pd.DataFrame(all_data)
    except Exception as e:
        logger.error(f"Failed to load JSON data: {e}")
        return None

    logger.info(f"Loaded {len(df)} match records from {parsed_dir}")

    if df.empty:
        logger.warning("DataFrame is empty - no data to process")
        return None

    # 2. Transform to Participant Level
    participants = []
    malformed_count = 0

    for _, row in df.iterrows():
        try:
            blue = json.loads(row["blue_team"])
            red = json.loads(row["red_team"])
            winner = row["winner"]

            # Blue participants
            for p in blue:
                others = [x["c"] for x in blue if x["c"] != p["c"]]
                enemies = [x["c"] for x in red]
                participants.append(
                    {
                        "match_id": row["match_id"],
                        "champ": p["c"],
                        "target_role": p["r"].upper(),
                        "win": (winner == "BLUE"),
                        "allies": others,
                        "enemies": enemies,
                    }
                )

            # Red participants
            for p in red:
                others = [x["c"] for x in red if x["c"] != p["c"]]
                enemies = [x["c"] for x in blue]
                participants.append(
                    {
                        "match_id": row["match_id"],
                        "champ": p["c"],
                        "target_role": p["r"].upper(),
                        "win": (winner == "RED"),
                        "allies": others,
                        "enemies": enemies,
                    }
                )
        except Exception:
            malformed_count += 1
            continue

    if not participants:
        logger.error("No valid participants extracted from matches")
        return None

    df = pd.DataFrame(participants)
    logger.info(
        f"Expanded to {len(df)} participant rows ({malformed_count} malformed matches skipped)"
    )

    # 3. Compute Global Winrates (baseline)
    global_grouped = df.groupby("champ")["win"].agg(["sum", "count"])
    global_winrates = (
        (global_grouped["sum"] + config.role_alpha)
        / (global_grouped["count"] + config.role_alpha + config.role_beta)
    ).to_dict()

    logger.info(f"Computed global winrates for {len(global_winrates)} champions")

    # 4. Compute Statistics
    logger.info("Computing role strength...")
    role_strength = compute_role_strength(df, config)

    logger.info("Computing synergy...")
    synergy = compute_synergy(df, global_winrates, config)

    logger.info("Computing counter...")
    counter = compute_counter(df, global_winrates, config)

    # Count statistics
    synergy_pairs = sum(len(allies) for allies in synergy.values())
    counter_pairs = sum(len(enemies) for enemies in counter.values())

    logger.info(f"Generated {synergy_pairs} synergy pairs, {counter_pairs} counter pairs")

    # 5. Create Validated Artifacts
    try:
        stats = ArtifactStats(
            role_strength=role_strength,
            synergy=synergy,
            counter=counter,
            global_winrates=global_winrates,
        )
    except Exception as e:
        logger.error(f"Failed to validate artifact stats: {e}")
        return None

    # Use human-readable run_id: 2026-01-25_10-27-34
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    manifest = ManifestData(
        run_id=run_id,
        timestamp=time.time(),
        rows_count=len(df),
        source=str(parsed_dir),
        config={
            "smoothing": f"role=Beta({config.role_alpha},{config.role_beta}), "
            f"pair=Beta({config.pair_alpha},{config.pair_beta})",
            "min_samples": config.min_samples,
        },
        data_quality={
            "malformed_count": malformed_count,
            "skipped_pct": round(malformed_count / max(len(df), 1) * 100, 2),
        },
        artifact_stats={
            "synergy_pairs": synergy_pairs,
            "counter_pairs": counter_pairs,
            "num_champions": len(global_winrates),
        },
    )

    # 6. Save Artifacts to runs/ subdirectory
    artifacts_dir = settings.artifacts_path
    runs_dir = artifacts_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_dir = runs_dir / run_id

    bundle = ArtifactBundle(stats=stats, manifest=manifest)
    save_artifact_bundle(run_dir, bundle)

    logger.info(f"Saved artifacts to {run_dir}")

    # 7. Update latest pointer
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "latest.json").write_text(
        json.dumps({"run": run_id}, indent=2), encoding="utf-8"
    )
    logger.info("Updated latest.json")

    return run_dir


if __name__ == "__main__": # pragma: no cover
    build_tables()
