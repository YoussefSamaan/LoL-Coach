"""Champion scoring using additive lift model.

This module implements the core scoring logic for champion recommendations.
It uses an additive lift approach in logit space to combine role strength,
synergy, and counter effects.

Note: This is NOT a true Naive Bayes model despite the historical naming.
It's an additive lift model that combines effects in logit space.
"""

from __future__ import annotations

import math
from collections.abc import Mapping as ABCMapping
from typing import Any

from app.ml.scoring.config import ScoringConfig


def _get_nested_any(mapping: ABCMapping[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely extract nested dictionary values (any type).

    Args:
        mapping: Dictionary to extract from.
        *keys: Sequence of keys to traverse.
        default: Default value if key path doesn't exist.

    Returns:
        Value at the key path (any type), or default if not found.

    Example:
        >>> stats = {"synergy": {"Ahri": {"Amumu": {"lift": 0.03, "count": 50}}}}
        >>> _get_nested_any(stats, "synergy", "Ahri", "Amumu")
        {'lift': 0.03, 'count': 50}
    """
    cur: Any = mapping
    for k in keys:
        if not isinstance(cur, ABCMapping) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _get_nested_float(mapping: ABCMapping[str, Any], *keys: str, default: float = 0.0) -> float:
    """Safely extract nested dictionary values as float.

    Args:
        mapping: Dictionary to extract from.
        *keys: Sequence of keys to traverse.
        default: Default value if key path doesn't exist or isn't numeric.

    Returns:
        Float value at the key path, or default if not found/not numeric.

    Example:
        >>> stats = {"role_strength": {"MID": {"Ahri": 0.52}}}
        >>> _get_nested_float(stats, "role_strength", "MID", "Ahri")
        0.52
        >>> _get_nested_float(stats, "role_strength", "TOP", "Ahri", default=0.5)
        0.5
    """
    val = _get_nested_any(mapping, *keys, default=None)
    return float(val) if isinstance(val, (int, float)) else default


def _clamp(x: float, lo: float, hi: float) -> float:
    """Clamp value to range [lo, hi].

    Args:
        x: Value to clamp.
        lo: Lower bound.
        hi: Upper bound.

    Returns:
        Clamped value.
    """
    return max(lo, min(hi, x))


def logit(p: float, epsilon: float = 1e-7) -> float:
    """Convert probability to logit (log-odds).

    Args:
        p: Probability in range (0, 1).
        epsilon: Small constant to avoid log(0) or log(inf).
                 Default 1e-7 provides numerical stability without
                 distorting smoothed probabilities.

    Returns:
        Log-odds: log(p / (1-p))

    Example:
        >>> logit(0.5)
        0.0
        >>> abs(logit(0.75) - 1.0986) < 0.01
        True
    """
    # Clamp to avoid inf
    p = max(epsilon, min(1 - epsilon, p))
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    """Convert logit (log-odds) back to probability.

    Uses numerically stable formulation to avoid overflow.

    Args:
        x: Log-odds value.

    Returns:
        Probability in range (0, 1).

    Example:
        >>> sigmoid(0.0)
        0.5
        >>> abs(sigmoid(1.0986) - 0.75) < 0.001
        True
    """
    # Numerically stable sigmoid to avoid overflow
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def score_candidate(
    *,
    candidate: str,
    role: str,
    allies: list[str],
    enemies: list[str],
    stats: ABCMapping[str, Any],
    config: ScoringConfig,
) -> tuple[float, list[str]]:
    """Score a candidate champion using additive lift model.

    Combines role strength, ally synergies, and enemy counters in logit space
    to produce a final win probability estimate.

    Algorithm:
        1. Get base role winrate for champion
        2. Convert to logit (log-odds)
        3. Add weighted synergy lifts (scaled to logit space)
        4. Add weighted counter lifts (scaled to logit space)
        5. Clamp total lifts to prevent extreme values
        6. Convert back to probability via sigmoid

    Args:
        candidate: Champion name to score (e.g., "Ahri").
        role: Target role (e.g., "MID").
        allies: List of allied champion names.
        enemies: List of enemy champion names.
        stats: Artifact statistics containing role_strength, synergy, counter.
        config: Scoring configuration (weights, scaling).

    Returns:
        Tuple of (probability, reasons) where:
        - probability: Estimated win probability [0, 1]
        - reasons: List of human-readable explanation strings

    Example:
        >>> config = ScoringConfig(synergy_weight=1.0, counter_weight=0.0, logit_scale=4.0)
        >>> stats = {
        ...     "role_strength": {"MID": {"Ahri": 0.52}},
        ...     "synergy": {"Ahri": {"Amumu": 0.03}},
        ...     "counter": {}
        ... }
        >>> prob, reasons = score_candidate(
        ...     candidate="Ahri",
        ...     role="MID",
        ...     allies=["Amumu"],
        ...     enemies=[],
        ...     stats=stats,
        ...     config=config
        ... )
        >>> prob > 0.52  # Should be higher than base due to synergy
        True
        >>> "Base Winrate" in reasons[0]
        True
    """
    reasons: list[str] = []

    # 1. Base Role Probability
    # Defaults to 0.5 if unknown (neutral)
    role_winrate = _get_nested_float(stats.get("role_strength", {}), role, candidate, default=0.5)

    # 2. Convert to Base Logit
    base_logit = logit(role_winrate)

    # 3. Extract Lifts
    # Lifts are stored as probability differences (e.g. +0.02 = +2% winrate)
    # We need to handle both old format (float) and new format (LiftStat dict)

    synergy_lifts = []
    for ally in allies:
        lift_data = _get_nested_any(stats.get("synergy", {}), candidate, ally, default=0.0)
        # Handle both old format (float) and new format (dict with 'lift' key)
        if isinstance(lift_data, dict):
            synergy_lifts.append(float(lift_data.get("lift", 0.0)))
        else:
            synergy_lifts.append(float(lift_data))

    counter_lifts = []
    for enemy in enemies:
        lift_data = _get_nested_any(stats.get("counter", {}), candidate, enemy, default=0.0)
        if isinstance(lift_data, dict):
            counter_lifts.append(float(lift_data.get("lift", 0.0)))
        else:
            counter_lifts.append(float(lift_data))

    synergy_score = sum(synergy_lifts)
    counter_score = sum(counter_lifts)

    # Clamp lift sums to prevent extreme values from noisy data
    # ±15% is already very extreme for aggregated lifts
    synergy_score = _clamp(synergy_score, -0.15, 0.15)
    counter_score = _clamp(counter_score, -0.15, 0.15)

    # 4. Apply Weights and Scaling
    # We scale probability deltas to logit space using config.logit_scale
    # Rationale: 1% winrate diff ≈ 0.04 logit change, so scale = 4.0
    total_logit = (
        base_logit
        + (synergy_score * config.synergy_weight * config.logit_scale)
        + (counter_score * config.counter_weight * config.logit_scale)
    )

    # 5. Convert back to probability
    final_prob = sigmoid(total_logit)

    # 6. Build explanation
    reasons.append(f"Base Winrate: {role_winrate:.1%}")
    if abs(synergy_score) > 0.005:
        reasons.append(f"Synergy Lift: {synergy_score:+.1%}")
    if abs(counter_score) > 0.005:
        reasons.append(f"Counter Lift: {counter_score:+.1%}")
    reasons.append(f"Final Prob: {final_prob:.1%}")

    return final_prob, reasons
