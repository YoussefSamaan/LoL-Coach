"""Champion scoring module.

This module provides the scoring logic for champion recommendations
using an additive lift model in logit space.

Key Components:
    - ScoringConfig: Configuration for scoring weights and parameters
    - score_candidate: Main scoring function

Example:
    >>> from app.ml.scoring import ScoringConfig, score_candidate
    >>>
    >>> config = ScoringConfig()
    >>> stats = load_artifacts()  # From training pipeline
    >>>
    >>> prob, reasons = score_candidate(
    ...     candidate="Ahri",
    ...     role="MID",
    ...     allies=["Amumu", "Jinx"],
    ...     enemies=["Zed", "LeeSin"],
    ...     stats=stats,
    ...     config=config
    ... )
    >>> print(f"Win probability: {prob:.1%}")
    >>> for reason in reasons:
    ...     print(f"  - {reason}")
"""

from app.ml.scoring.config import ScoringConfig
from app.ml.scoring.inference import score_candidate, logit, sigmoid

__all__ = [
    "ScoringConfig",
    "score_candidate",
    "logit",
    "sigmoid",
]
