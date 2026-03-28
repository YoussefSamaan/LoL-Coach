"""Artifact manifest metadata.

This module defines the ManifestData model for tracking provenance,
configuration, and metrics for reproducibility.
"""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict


class ManifestData(BaseModel):
    """Artifact manifest metadata.

    Tracks provenance, configuration, and metrics for reproducibility
    and debugging. Every training run produces a manifest alongside
    the statistics.

    Attributes:
        run_id: Unique identifier for this training run (e.g., "20260124_120000").
        version: Semantic version of the model (e.g., "v1.0.0").
        timestamp: Unix timestamp when training completed.
        rows_count: Number of participant rows processed (not matches).
        source: Path to source data directory.
        config: Configuration used for this run (smoothing params, etc.).
        data_quality: Data quality metrics (malformed_count, skipped_pct, etc.).
        artifact_stats: Artifact statistics (num_synergy_pairs, num_counter_pairs, etc.).

    Example:
        >>> manifest = ManifestData(
        ...     run_id="20260124_120000",
        ...     version="v1.0.0",
        ...     timestamp=1706112000.0,
        ...     rows_count=5000,
        ...     source="/data/parsed",
        ...     config={"smoothing": "Beta(5,5)"},
        ...     data_quality={"malformed_count": 10, "skipped_pct": 0.2},
        ...     artifact_stats={"synergy_pairs": 1500, "counter_pairs": 1500}
        ... )
    """

    run_id: str
    version: str = "v1.0.0"
    timestamp: float
    rows_count: int = Field(..., gt=0)
    source: str

    # Configuration used for this run
    config: dict[str, object] = Field(default_factory=dict)

    # Data quality metrics
    data_quality: dict[str, int | float] = Field(default_factory=dict)

    # Artifact statistics
    artifact_stats: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)
