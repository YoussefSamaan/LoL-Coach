"""Scoring configuration for champion recommendation.

This module defines the configuration for the additive lift scoring model
used to recommend champions based on draft state.
"""

from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict


class ScoringConfig(BaseModel):
    """Configuration for additive lift scoring model.

    This model uses an additive approach in logit space to combine:
    - Base role-specific winrate
    - Synergy effects with allies
    - Counter effects against enemies

    Attributes:
        role_strength_weight: Weight for base role winrate (typically 1.0).
                              Controls how much the champion's inherent strength
                              in the role affects the score.

        synergy_weight: Weight for ally synergy effects (0-1 range).
                        Controls how much champion synergies affect the score.
                        Lower values = less emphasis on team composition.

        counter_weight: Weight for enemy counter effects (0-1 range).
                        Controls how much enemy matchups affect the score.
                        Lower values = less emphasis on counters.

        off_role_penalty: Penalty for off-role picks (not yet implemented).
                          Reserved for future use.

        logit_scale: Scaling factor to convert winrate lifts to logit space.
                     Rationale: 1% winrate diff ≈ 0.04 logit change
                     So we scale by 1/0.01 * 0.04 = 4.0

    Example:
        >>> # Default config (balanced)
        >>> config = ScoringConfig()
        >>>
        >>> # Emphasize role strength over synergies
        >>> config = ScoringConfig(
        ...     role_strength_weight=1.0,
        ...     synergy_weight=0.3,
        ...     counter_weight=0.3
        ... )
        >>>
        >>> # Emphasize team composition
        >>> config = ScoringConfig(
        ...     synergy_weight=0.8,
        ...     counter_weight=0.8
        ... )
    """

    role_strength_weight: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Weight for base role winrate"
    )
    synergy_weight: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Weight for ally synergy effects"
    )
    counter_weight: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Weight for enemy counter effects"
    )
    off_role_penalty: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Penalty for off-role picks (not yet implemented)"
    )
    logit_scale: float = Field(
        default=4.0, gt=0.0, description="Scaling factor for winrate lifts in logit space"
    )

    model_config = ConfigDict(frozen=True)
