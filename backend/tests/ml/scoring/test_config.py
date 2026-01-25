"""Tests for ScoringConfig model."""

import pytest
from pydantic import ValidationError

from app.ml.scoring import ScoringConfig


class TestScoringConfig:
    """Tests for ScoringConfig model."""

    def test_default_config(self):
        """Default ScoringConfig should have balanced values."""
        config = ScoringConfig()

        assert config.role_strength_weight == 1.0
        assert config.synergy_weight == 0.5
        assert config.counter_weight == 0.5
        assert config.off_role_penalty == 0.0
        assert config.logit_scale == 4.0

    def test_custom_config(self):
        """Custom ScoringConfig should accept valid values."""
        config = ScoringConfig(
            role_strength_weight=0.9, synergy_weight=0.8, counter_weight=0.3, logit_scale=5.0
        )

        assert config.role_strength_weight == 0.9
        assert config.synergy_weight == 0.8
        assert config.counter_weight == 0.3
        assert config.logit_scale == 5.0

    def test_negative_weight(self):
        """Negative weights should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScoringConfig(synergy_weight=-0.5)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_weight_too_high(self):
        """Weights > 1.0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScoringConfig(role_strength_weight=1.5)
        assert "less than or equal to 1" in str(exc_info.value)

    def test_zero_logit_scale(self):
        """logit_scale = 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScoringConfig(logit_scale=0.0)
        assert "greater than 0" in str(exc_info.value)

    def test_negative_logit_scale(self):
        """Negative logit_scale should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScoringConfig(logit_scale=-1.0)
        assert "greater than 0" in str(exc_info.value)

    def test_immutability(self):
        """ScoringConfig should be immutable (frozen)."""
        config = ScoringConfig()
        with pytest.raises(ValidationError):
            config.synergy_weight = 0.8

    def test_emphasize_role_strength(self):
        """Config can emphasize role strength over synergies."""
        config = ScoringConfig(role_strength_weight=1.0, synergy_weight=0.2, counter_weight=0.2)
        assert config.role_strength_weight > config.synergy_weight
        assert config.role_strength_weight > config.counter_weight

    def test_emphasize_team_composition(self):
        """Config can emphasize team composition."""
        config = ScoringConfig(synergy_weight=0.9, counter_weight=0.9)
        assert config.synergy_weight > config.role_strength_weight / 2
        assert config.counter_weight > config.role_strength_weight / 2
