"""Tests for ArtifactStats model."""

import pytest
from pydantic import ValidationError

from app.ml.training import ArtifactStats, LiftStat


class TestArtifactStats:
    """Tests for ArtifactStats model."""

    def test_valid_artifact_stats(self):
        """Valid ArtifactStats should be created successfully."""
        stats = ArtifactStats(
            role_strength={"MID": {"Ahri": 0.52, "Zed": 0.51}},
            synergy={"Ahri": {"Amumu": LiftStat(lift=0.03, count=50)}},
            counter={"Ahri": {"Zed": LiftStat(lift=-0.02, count=75)}},
            global_winrates={"Ahri": 0.505, "Zed": 0.498},
        )

        assert stats.role_strength["MID"]["Ahri"] == 0.52
        assert stats.synergy["Ahri"]["Amumu"].lift == 0.03
        assert stats.counter["Ahri"]["Zed"].count == 75
        assert stats.global_winrates["Ahri"] == 0.505

    def test_empty_structures(self):
        """Empty dictionaries should be allowed."""
        stats = ArtifactStats(role_strength={}, synergy={}, counter={}, global_winrates={})
        assert len(stats.role_strength) == 0

    def test_invalid_role_strength_winrate_high(self):
        """Winrate > 1.0 in role_strength should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactStats(
                role_strength={"MID": {"Ahri": 1.5}}, synergy={}, counter={}, global_winrates={}
            )
        assert "Invalid winrate" in str(exc_info.value)
        assert "must be in [0.0, 1.0]" in str(exc_info.value)

    def test_invalid_role_strength_winrate_low(self):
        """Winrate < 0.0 in role_strength should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactStats(
                role_strength={"MID": {"Ahri": -0.1}}, synergy={}, counter={}, global_winrates={}
            )
        assert "Invalid winrate" in str(exc_info.value)

    def test_invalid_global_winrate(self):
        """Invalid global winrate should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactStats(role_strength={}, synergy={}, counter={}, global_winrates={"Ahri": 2.0})
        assert "Invalid global winrate" in str(exc_info.value)

    def test_multiple_roles(self):
        """Multiple roles should work correctly."""
        stats = ArtifactStats(
            role_strength={
                "MID": {"Ahri": 0.52},
                "TOP": {"Aatrox": 0.51},
                "JUNGLE": {"Amumu": 0.50},
            },
            synergy={},
            counter={},
            global_winrates={"Ahri": 0.52, "Aatrox": 0.51, "Amumu": 0.50},
        )
        assert len(stats.role_strength) == 3

    def test_immutability(self):
        """ArtifactStats should be immutable (frozen)."""
        stats = ArtifactStats(
            role_strength={"MID": {"Ahri": 0.52}},
            synergy={},
            counter={},
            global_winrates={"Ahri": 0.52},
        )
        with pytest.raises(ValidationError):
            stats.role_strength = {}
