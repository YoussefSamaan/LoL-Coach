"""Bayesian smoothing configuration.

This module defines the SmoothingConfig model for controlling how
the training pipeline handles low-sample scenarios.
"""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict


class SmoothingConfig(BaseModel):
    """Bayesian smoothing configuration.

    Uses Beta(alpha, beta) prior for binomial proportions to handle
    low-sample scenarios gracefully.

    Key Concepts:
        - alpha = beta gives a 50% prior (neutral)
        - alpha + beta controls strength (equivalent sample size)
        - Higher values = more smoothing toward prior

    Attributes:
        role_alpha: Alpha parameter for role-specific winrates (default: 5.0).
        role_beta: Beta parameter for role-specific winrates (default: 5.0).
                   Beta(5, 5) = 50% prior with strength of 10 games.

        pair_alpha: Alpha parameter for pairwise synergy/counter (default: 10.0).
        pair_beta: Beta parameter for pairwise synergy/counter (default: 10.0).
                   Beta(10, 10) = 50% prior with strength of 20 games.
                   Stronger smoothing for sparse pairs.

        min_samples: Minimum number of games required for a pair to be included
                     in synergy/counter tables (default: 5).

    Recommendations:
        - Role strength: Beta(5, 5) - moderate smoothing
        - Synergy/Counter: Beta(10, 10) - stronger smoothing for sparse pairs
        - min_samples: 5-10 depending on data volume

    Example:
        >>> # Default config (recommended)
        >>> config = SmoothingConfig()
        >>>
        >>> # Custom config with stronger smoothing
        >>> config = SmoothingConfig(
        ...     role_alpha=10.0,
        ...     role_beta=10.0,
        ...     pair_alpha=20.0,
        ...     pair_beta=20.0,
        ...     min_samples=10
        ... )
        >>>
        >>> # Compute smoothed winrate
        >>> wins, games = 3, 5
        >>> smoothed_wr = (wins + config.role_alpha) / (games + config.role_alpha + config.role_beta)
        >>> print(f"Raw: {wins/games:.1%}, Smoothed: {smoothed_wr:.1%}")
        Raw: 60.0%, Smoothed: 53.3%
    """

    role_alpha: float = Field(default=5.0, gt=0.0, description="Alpha for role-specific winrates")
    role_beta: float = Field(default=5.0, gt=0.0, description="Beta for role-specific winrates")
    pair_alpha: float = Field(
        default=10.0, gt=0.0, description="Alpha for pairwise synergy/counter"
    )
    pair_beta: float = Field(default=10.0, gt=0.0, description="Beta for pairwise synergy/counter")
    min_samples: int = Field(default=5, ge=1, description="Minimum games for pair inclusion")

    model_config = ConfigDict(frozen=True)
