"""Training pipeline models and configuration.

This module provides Pydantic models for the ML training pipeline,
ensuring type safety and validation for all training artifacts.

Key Models:
    - LiftStat: Pairwise lift statistic with sample size
    - ArtifactStats: Complete artifact statistics structure
    - ManifestData: Artifact manifest metadata
    - SmoothingConfig: Bayesian smoothing configuration

Example:
    >>> from app.ml.training import SmoothingConfig, LiftStat
    >>> config = SmoothingConfig(role_alpha=5.0, role_beta=5.0)
    >>> lift = LiftStat(lift=0.05, count=100)
    >>> print(f"Lift: {lift.lift:.1%} from {lift.count} games")
    Lift: 5.0% from 100 games
"""

from app.ml.training.lift_stat import LiftStat
from app.ml.training.smoothing_config import SmoothingConfig
from app.ml.training.artifact_stats import ArtifactStats, Role, Champion
from app.ml.training.manifest_data import ManifestData

__all__ = [
    "LiftStat",
    "ArtifactStats",
    "ManifestData",
    "SmoothingConfig",
    "Role",
    "Champion",
]
