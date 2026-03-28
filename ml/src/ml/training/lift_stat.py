"""Pairwise lift statistic with sample size.

This module defines the LiftStat model for storing synergy and counter
statistics with their associated sample counts.
"""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict


class LiftStat(BaseModel):
    """Pairwise lift statistic with sample size.

    Represents how much a champion's winrate changes when paired with
    a specific ally or matched against a specific enemy.

    Attributes:
        lift: Winrate delta from baseline (e.g., +0.05 = +5% winrate increase).
              Range: [-1.0, 1.0] where negative means worse, positive means better.
        count: Number of games this pair appeared together. Used for confidence
               weighting and filtering low-sample pairs.

    Example:
        >>> # Ahri + Amumu synergy: +3% winrate from 50 games
        >>> synergy = LiftStat(lift=0.03, count=50)
        >>>
        >>> # Ahri vs Zed counter: -2% winrate from 75 games
        >>> counter = LiftStat(lift=-0.02, count=75)
    """

    lift: float = Field(..., ge=-1.0, le=1.0, description="Winrate delta from baseline")
    count: int = Field(..., gt=0, description="Number of games (sample size)")

    model_config = ConfigDict(frozen=True)
