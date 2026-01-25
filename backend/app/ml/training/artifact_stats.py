"""Complete artifact statistics structure.

This module defines the ArtifactStats model which is the main output
of the training process and input to inference.
"""

from __future__ import annotations
from pydantic import BaseModel, field_validator, ConfigDict

from app.ml.training.lift_stat import LiftStat

# Type aliases for clarity
Role = str
Champion = str


class ArtifactStats(BaseModel):
    """Complete artifact statistics structure.

    Stores all computed statistics from the training pipeline.
    This is the main output of the training process and input to inference.

    Attributes:
        role_strength: Role-specific champion winrates.
            Structure: {Role: {Champion: winrate}}
            Example: {"MID": {"Ahri": 0.52, "Zed": 0.51}}

        synergy: Ally synergy lifts with sample counts.
            Structure: {Champion: {Ally: LiftStat}}
            Example: {"Ahri": {"Amumu": LiftStat(lift=0.03, count=50)}}

        counter: Enemy counter lifts with sample counts.
            Structure: {Champion: {Enemy: LiftStat}}
            Example: {"Ahri": {"Zed": LiftStat(lift=-0.02, count=75)}}

        global_winrates: Baseline winrates per champion (across all roles).
            Structure: {Champion: winrate}
            Example: {"Ahri": 0.505, "Zed": 0.498}

    Example:
        >>> stats = ArtifactStats(
        ...     role_strength={"MID": {"Ahri": 0.52}},
        ...     synergy={"Ahri": {"Amumu": LiftStat(lift=0.03, count=50)}},
        ...     counter={"Ahri": {"Zed": LiftStat(lift=-0.02, count=75)}},
        ...     global_winrates={"Ahri": 0.505}
        ... )
    """

    role_strength: dict[Role, dict[Champion, float]]
    synergy: dict[Champion, dict[Champion, LiftStat]]
    counter: dict[Champion, dict[Champion, LiftStat]]
    global_winrates: dict[Champion, float]

    @field_validator("role_strength")
    @classmethod
    def validate_role_strength(cls, v: dict[Role, dict[Champion, float]]) -> dict:
        """Validate all winrates are in valid range [0, 1].

        Args:
            v: Role strength dictionary to validate.

        Returns:
            Validated dictionary.

        Raises:
            ValueError: If any winrate is outside [0, 1].
        """
        for role, champs in v.items():
            for champ, wr in champs.items():
                if not (0.0 <= wr <= 1.0):
                    raise ValueError(
                        f"Invalid winrate for {role}/{champ}: {wr} (must be in [0.0, 1.0])"
                    )
        return v

    @field_validator("global_winrates")
    @classmethod
    def validate_global_winrates(cls, v: dict[Champion, float]) -> dict:
        """Validate all global winrates are in valid range [0, 1].

        Args:
            v: Global winrates dictionary to validate.

        Returns:
            Validated dictionary.

        Raises:
            ValueError: If any winrate is outside [0, 1].
        """
        for champ, wr in v.items():
            if not (0.0 <= wr <= 1.0):
                raise ValueError(
                    f"Invalid global winrate for {champ}: {wr} (must be in [0.0, 1.0])"
                )
        return v

    model_config = ConfigDict(frozen=True)
