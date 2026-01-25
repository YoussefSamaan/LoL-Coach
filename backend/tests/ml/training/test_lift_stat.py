"""Tests for LiftStat model."""

import pytest
from pydantic import ValidationError

from app.ml.training import LiftStat


class TestLiftStat:
    """Tests for LiftStat model."""

    def test_valid_lift_stat(self):
        """Valid LiftStat should be created successfully."""
        lift = LiftStat(lift=0.05, count=100)
        assert lift.lift == 0.05
        assert lift.count == 100

    def test_negative_lift(self):
        """Negative lifts should be allowed (counter effects)."""
        lift = LiftStat(lift=-0.03, count=50)
        assert lift.lift == -0.03
        assert lift.count == 50

    def test_lift_out_of_range_high(self):
        """Lift > 1.0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LiftStat(lift=1.5, count=100)
        assert "less than or equal to 1" in str(exc_info.value)

    def test_lift_out_of_range_low(self):
        """Lift < -1.0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LiftStat(lift=-1.5, count=100)
        assert "greater than or equal to -1" in str(exc_info.value)

    def test_zero_count(self):
        """Count = 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LiftStat(lift=0.05, count=0)
        assert "greater than 0" in str(exc_info.value)

    def test_negative_count(self):
        """Negative count should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LiftStat(lift=0.05, count=-10)
        assert "greater than 0" in str(exc_info.value)

    def test_immutability(self):
        """LiftStat should be immutable (frozen)."""
        lift = LiftStat(lift=0.05, count=100)
        with pytest.raises(ValidationError):
            lift.lift = 0.10
