"""Tests for SmoothingConfig model."""

import pytest
from pydantic import ValidationError

from app.ml.training import SmoothingConfig


class TestSmoothingConfig:
    """Tests for SmoothingConfig model."""

    def test_default_config(self):
        """Default SmoothingConfig should have recommended values."""
        config = SmoothingConfig()

        assert config.role_alpha == 5.0
        assert config.role_beta == 5.0
        assert config.pair_alpha == 10.0
        assert config.pair_beta == 10.0
        assert config.min_samples == 5

    def test_custom_config(self):
        """Custom SmoothingConfig should accept valid values."""
        config = SmoothingConfig(
            role_alpha=10.0, role_beta=10.0, pair_alpha=20.0, pair_beta=20.0, min_samples=10
        )

        assert config.role_alpha == 10.0
        assert config.pair_alpha == 20.0
        assert config.min_samples == 10

    def test_zero_alpha(self):
        """Alpha = 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SmoothingConfig(role_alpha=0.0)
        assert "greater than 0" in str(exc_info.value)

    def test_negative_alpha(self):
        """Negative alpha should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SmoothingConfig(role_alpha=-1.0)
        assert "greater than 0" in str(exc_info.value)

    def test_zero_min_samples(self):
        """min_samples = 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SmoothingConfig(min_samples=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_negative_min_samples(self):
        """Negative min_samples should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SmoothingConfig(min_samples=-5)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_immutability(self):
        """SmoothingConfig should be immutable (frozen)."""
        config = SmoothingConfig()
        with pytest.raises(ValidationError):
            config.role_alpha = 10.0

    def test_smoothing_calculation(self):
        """Test that smoothing formula works as expected."""
        config = SmoothingConfig(role_alpha=5.0, role_beta=5.0)

        # With 3 wins in 5 games:
        # Raw winrate: 3/5 = 60%
        # Smoothed: (3+5)/(5+5+5) = 8/15 = 53.3%
        wins, games = 3, 5
        smoothed_wr = (wins + config.role_alpha) / (games + config.role_alpha + config.role_beta)

        assert abs(smoothed_wr - 0.533) < 0.001

        # With 300 wins in 500 games:
        # Raw winrate: 300/500 = 60%
        # Smoothed: (300+5)/(500+5+5) = 305/510 = 59.8%
        # (Less smoothing effect with more data)
        wins, games = 300, 500
        smoothed_wr = (wins + config.role_alpha) / (games + config.role_alpha + config.role_beta)

        assert abs(smoothed_wr - 0.598) < 0.001
