"""Tests for scoring inference functions."""

import math

from app.ml.scoring import ScoringConfig, score_candidate, logit, sigmoid


class TestLogitSigmoid:
    """Tests for logit and sigmoid functions."""

    def test_logit_neutral(self):
        """Logit of 0.5 should be 0."""
        assert abs(logit(0.5)) < 0.001

    def test_logit_high_probability(self):
        """Logit of high probability should be positive."""
        assert logit(0.75) > 0
        assert abs(logit(0.75) - 1.0986) < 0.01

    def test_logit_low_probability(self):
        """Logit of low probability should be negative."""
        assert logit(0.25) < 0
        assert abs(logit(0.25) - (-1.0986)) < 0.01

    def test_logit_clamping(self):
        """Logit should clamp extreme values to avoid inf."""
        # Should not raise error or return inf
        result = logit(0.0)
        assert math.isfinite(result)

        result = logit(1.0)
        assert math.isfinite(result)

    def test_sigmoid_neutral(self):
        """Sigmoid of 0 should be 0.5."""
        assert abs(sigmoid(0.0) - 0.5) < 0.001

    def test_sigmoid_positive(self):
        """Sigmoid of positive value should be > 0.5."""
        assert sigmoid(1.0) > 0.5
        assert abs(sigmoid(1.0986) - 0.75) < 0.01

    def test_sigmoid_negative(self):
        """Sigmoid of negative value should be < 0.5."""
        assert sigmoid(-1.0) < 0.5
        assert abs(sigmoid(-1.0986) - 0.25) < 0.01

    def test_logit_sigmoid_inverse(self):
        """Sigmoid should be inverse of logit."""
        p = 0.7
        assert abs(sigmoid(logit(p)) - p) < 0.001


class TestScoreCandidate:
    """Tests for score_candidate function."""

    def test_basic_scoring(self):
        """Basic scoring should work with simple stats."""
        config = ScoringConfig()
        stats = {
            "role_strength": {"MID": {"Ahri": 0.55}},
            "synergy": {"Ahri": {"Amumu": 0.05}},
            "counter": {"Ahri": {"Zed": 0.02}},
        }

        score, reasons = score_candidate(
            candidate="Ahri",
            role="MID",
            allies=["Amumu"],
            enemies=["Zed"],
            stats=stats,
            config=config,
        )

        # Score should be higher than base due to positive synergy and counter
        assert score > 0.55
        assert len(reasons) == 4
        assert "Base Winrate: 55.0%" in reasons
        assert "Synergy Lift: +5.0%" in reasons
        assert "Counter Lift: +2.0%" in reasons

    def test_unknown_champion(self):
        """Unknown champion should default to 50% winrate."""
        config = ScoringConfig()
        stats = {
            "role_strength": {},
            "synergy": {},
            "counter": {},
        }

        score, reasons = score_candidate(
            candidate="UnknownChamp", role="MID", allies=[], enemies=[], stats=stats, config=config
        )

        # Should default to neutral 50%
        assert abs(score - 0.5) < 0.01
        assert "Base Winrate: 50.0%" in reasons

    def test_negative_counter(self):
        """Negative counter should decrease score."""
        config = ScoringConfig()
        stats = {
            "role_strength": {"MID": {"Ahri": 0.50}},
            "synergy": {},
            "counter": {"Ahri": {"Zed": -0.05}},  # Bad matchup
        }

        score, reasons = score_candidate(
            candidate="Ahri", role="MID", allies=[], enemies=["Zed"], stats=stats, config=config
        )

        # Score should be lower than base due to bad matchup
        assert score < 0.50
        assert "Counter Lift: -5.0%" in reasons

    def test_multiple_allies_and_enemies(self):
        """Should handle multiple allies and enemies."""
        config = ScoringConfig()
        stats = {
            "role_strength": {"MID": {"Ahri": 0.52}},
            "synergy": {
                "Ahri": {
                    "Amumu": 0.02,
                    "Jinx": 0.01,
                }
            },
            "counter": {
                "Ahri": {
                    "Zed": -0.03,
                    "LeeSin": 0.01,
                }
            },
        }

        score, reasons = score_candidate(
            candidate="Ahri",
            role="MID",
            allies=["Amumu", "Jinx"],
            enemies=["Zed", "LeeSin"],
            stats=stats,
            config=config,
        )

        # Should aggregate all synergies and counters
        assert "Synergy Lift: +3.0%" in reasons  # 2% + 1%
        assert "Counter Lift: -2.0%" in reasons  # -3% + 1%

    def test_custom_weights(self):
        """Custom weights should affect scoring."""
        stats = {
            "role_strength": {"MID": {"Ahri": 0.50}},
            "synergy": {"Ahri": {"Amumu": 0.05}},
            "counter": {},
        }

        # High synergy weight
        config_high = ScoringConfig(synergy_weight=1.0)
        score_high, _ = score_candidate(
            candidate="Ahri",
            role="MID",
            allies=["Amumu"],
            enemies=[],
            stats=stats,
            config=config_high,
        )

        # Low synergy weight
        config_low = ScoringConfig(synergy_weight=0.1)
        score_low, _ = score_candidate(
            candidate="Ahri",
            role="MID",
            allies=["Amumu"],
            enemies=[],
            stats=stats,
            config=config_low,
        )

        # Higher weight should produce higher score
        assert score_high > score_low

    def test_new_artifact_format_with_lift_stat(self):
        """Should handle new artifact format with LiftStat dicts."""
        config = ScoringConfig()
        stats = {
            "role_strength": {"MID": {"Ahri": 0.52}},
            "synergy": {
                "Ahri": {
                    "Amumu": {"lift": 0.06, "count": 50}  # New format, larger lift
                }
            },
            "counter": {
                "Ahri": {
                    "Zed": {"lift": -0.04, "count": 75}  # New format, larger lift
                }
            },
        }

        score, reasons = score_candidate(
            candidate="Ahri",
            role="MID",
            allies=["Amumu"],
            enemies=["Zed"],
            stats=stats,
            config=config,
        )

        # Should extract lift values correctly
        assert score >= 0.52  # Positive synergy, negative counter (net positive)
        assert "Synergy Lift: +6.0%" in reasons
        assert "Counter Lift: -4.0%" in reasons

    def test_small_lifts_not_shown(self):
        """Very small lifts should not appear in reasons."""
        config = ScoringConfig()
        stats = {
            "role_strength": {"MID": {"Ahri": 0.50}},
            "synergy": {"Ahri": {"Amumu": 0.001}},  # Very small
            "counter": {},
        }

        score, reasons = score_candidate(
            candidate="Ahri", role="MID", allies=["Amumu"], enemies=[], stats=stats, config=config
        )

        # Should not show synergy lift (< 0.5%)
        synergy_reasons = [r for r in reasons if "Synergy" in r]
        assert len(synergy_reasons) == 0
