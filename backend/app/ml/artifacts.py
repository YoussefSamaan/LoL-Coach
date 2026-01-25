"""Artifact loading and saving for ML models.

This module handles serialization and deserialization of ML artifacts,
including statistics and metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.ml.training import ArtifactStats, ManifestData
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ArtifactBundle(BaseModel):
    """Bundle of ML artifacts including stats and manifest.

    Attributes:
        stats: Training statistics (role strength, synergy, counter, global winrates).
        manifest: Metadata about the training run (provenance, config, metrics).

    Example:
        >>> from pathlib import Path
        >>> bundle = load_artifact_bundle(Path("artifacts/runs/20260124_120000"))
        >>> print(f"Loaded {len(bundle.stats.global_winrates)} champions")
        >>> print(f"Run ID: {bundle.manifest.run_id}")
    """

    stats: ArtifactStats
    manifest: ManifestData

    model_config = ConfigDict(frozen=True)


def load_artifact_bundle(run_dir: Path) -> ArtifactBundle:
    """Load ML artifacts from a run directory.

    Loads and validates both statistics and manifest files.

    Args:
        run_dir: Directory containing stats.json and manifest.json.
                 Example: artifacts/runs/20260124_120000/

    Returns:
        ArtifactBundle with validated stats and manifest.

    Raises:
        FileNotFoundError: If stats.json or manifest.json doesn't exist.
        json.JSONDecodeError: If files contain invalid JSON.
        pydantic.ValidationError: If data doesn't match expected schema.

    Example:
        >>> from pathlib import Path
        >>> bundle = load_artifact_bundle(Path("artifacts/runs/20260124_120000"))
        >>> assert bundle.stats.global_winrates["Ahri"] > 0
    """
    stats_file = run_dir / "stats.json"
    manifest_file = run_dir / "manifest.json"

    # Check files exist
    if not stats_file.exists():
        raise FileNotFoundError(f"Stats file not found: {stats_file}")
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_file}")

    # Load JSON
    try:
        stats_data = json.loads(stats_file.read_text(encoding="utf-8"))
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {run_dir}: {e}")
        raise

    # Parse and validate with Pydantic
    try:
        stats = ArtifactStats(**stats_data)
        manifest = ManifestData(**manifest_data)
    except Exception as e:
        logger.error(f"Failed to validate artifacts from {run_dir}: {e}")
        raise

    logger.info(
        f"Loaded artifacts from {run_dir.name}: "
        f"{len(stats.global_winrates)} champions, "
        f"{manifest.rows_count} rows"
    )

    return ArtifactBundle(stats=stats, manifest=manifest)


def save_artifact_bundle(run_dir: Path, bundle: ArtifactBundle) -> None:
    """Save ML artifacts to a run directory.

    Saves both statistics and manifest as formatted JSON files.

    Args:
        run_dir: Directory to save artifacts to.
                 Will be created if it doesn't exist.
        bundle: Artifact bundle to save.

    Example:
        >>> from pathlib import Path
        >>> from app.ml.training import ArtifactStats, ManifestData
        >>>
        >>> stats = ArtifactStats(
        ...     role_strength={"MID": {"Ahri": 0.52}},
        ...     synergy={},
        ...     counter={},
        ...     global_winrates={"Ahri": 0.52}
        ... )
        >>> manifest = ManifestData(
        ...     run_id="20260124_120000",
        ...     timestamp=1706112000.0,
        ...     rows_count=5000,
        ...     source="/data/parsed"
        ... )
        >>> bundle = ArtifactBundle(stats=stats, manifest=manifest)
        >>> save_artifact_bundle(Path("artifacts/runs/20260124_120000"), bundle)
    """
    run_dir.mkdir(parents=True, exist_ok=True)

    # Convert Pydantic models to dict for JSON serialization
    stats_dict = _pydantic_to_dict(bundle.stats)
    manifest_dict = bundle.manifest.model_dump()

    # Save with formatting
    (run_dir / "stats.json").write_text(
        json.dumps(stats_dict, indent=2, sort_keys=True), encoding="utf-8"
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest_dict, indent=2, sort_keys=True), encoding="utf-8"
    )

    logger.info(f"Saved artifacts to {run_dir}")


def _pydantic_to_dict(stats: ArtifactStats) -> dict[str, Any]:
    """Convert ArtifactStats to dict, handling LiftStat serialization.

    Args:
        stats: ArtifactStats to convert.

    Returns:
        Dictionary suitable for JSON serialization.
    """
    return {
        "role_strength": stats.role_strength,
        "synergy": {
            champ: {
                ally: {"lift": lift_stat.lift, "count": lift_stat.count}
                for ally, lift_stat in allies.items()
            }
            for champ, allies in stats.synergy.items()
        },
        "counter": {
            champ: {
                enemy: {"lift": lift_stat.lift, "count": lift_stat.count}
                for enemy, lift_stat in enemies.items()
            }
            for champ, enemies in stats.counter.items()
        },
        "global_winrates": stats.global_winrates,
    }
