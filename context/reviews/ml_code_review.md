# ML Code Review - Naive Bayes Implementation

## Executive Summary

The current Naive Bayes implementation is **functional and well-structured** for an MVP, but there are several improvements needed to meet senior MLE standards. The code demonstrates good software engineering practices (type hints, dataclasses, separation of concerns) but lacks some ML engineering best practices around model versioning, validation, monitoring, and statistical rigor.

**Overall Grade: B+ (Good foundation, needs production hardening)**

---

## Detailed Review by Component

### 1. **artifacts.py** ✅ Good

**Strengths:**
- Clean dataclass design with immutability (`frozen=True`)
- Proper JSON serialization with encoding
- Simple, focused API

**Improvements Needed:**

#### 1.1 Add Schema Validation
```python
# Current: No validation of stats structure
# Recommended: Add Pydantic models for type safety

from pydantic import BaseModel, Field

class StatsSchema(BaseModel):
    role_strength: dict[str, dict[str, float]]
    synergy: dict[str, dict[str, float]]
    counter: dict[str, dict[str, float]]
    global_winrates: dict[str, float]

class ManifestSchema(BaseModel):
    run_id: str
    timestamp: float
    rows_count: int = Field(gt=0)
    source: str
```

#### 1.2 Add Checksum/Integrity Validation
```python
import hashlib

def save_artifact_bundle(run_dir: Path, bundle: ArtifactBundle) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    
    stats_json = json.dumps(bundle.stats, indent=2, sort_keys=True)
    manifest_json = json.dumps(bundle.manifest, indent=2, sort_keys=True)
    
    # Save files
    (run_dir / "stats.json").write_text(stats_json, encoding="utf-8")
    (run_dir / "manifest.json").write_text(manifest_json, encoding="utf-8")
    
    # Save checksums for integrity validation
    checksums = {
        "stats.json": hashlib.sha256(stats_json.encode()).hexdigest(),
        "manifest.json": hashlib.sha256(manifest_json.encode()).hexdigest(),
    }
    (run_dir / "checksums.json").write_text(
        json.dumps(checksums, indent=2), encoding="utf-8"
    )
```

---

### 2. **build_tables.py** ⚠️ Needs Improvement

**Strengths:**
- Good separation of concerns (compute functions)
- Proper logging
- Beta smoothing for low-count scenarios
- Handles edge cases (empty data, missing dirs)

**Critical Issues:**

#### 2.1 **Statistical Issues**

**Problem 1: Inconsistent Smoothing**
```python
# Line 23: Beta(1,1) smoothing
grouped["winrate"] = (grouped["sum"] + 1) / (grouped["count"] + 2)
```
- Beta(1,1) is uniform prior (no information)
- For LoL, we know average winrate ≈ 50%
- **Recommendation**: Use Beta(α, β) where α = β for 50% prior, with α+β controlling strength

```python
# Recommended: Configurable prior
@dataclass
class SmoothingConfig:
    prior_alpha: float = 5.0  # Equivalent to 5 wins
    prior_beta: float = 5.0   # Equivalent to 5 losses
    # This gives 50% prior with strength of 10 games

def compute_role_strength(df: pd.DataFrame, config: SmoothingConfig) -> dict:
    grouped = df.groupby(["target_role", "champ"])["win"].agg(["sum", "count"])
    grouped["winrate"] = (
        (grouped["sum"] + config.prior_alpha) / 
        (grouped["count"] + config.prior_alpha + config.prior_beta)
    )
```

**Problem 2: Lift Calculation Ignores Sample Size**
```python
# Line 61: No confidence weighting
lift = row["pair_winrate"] - base
```
- A lift from 1 game has same weight as lift from 1000 games
- **Recommendation**: Add confidence intervals or Bayesian credible intervals

```python
def compute_synergy_with_confidence(
    df: pd.DataFrame, 
    global_winrates: dict,
    min_samples: int = 10
) -> dict:
    """Compute synergy with confidence-based filtering."""
    mini_df = df[["champ", "allies", "win"]].copy()
    exploded = mini_df.explode("allies")
    
    grouped = exploded.groupby(["champ", "allies"])["win"].agg(["sum", "count"])
    
    # Filter low-sample pairs
    grouped = grouped[grouped["count"] >= min_samples]
    
    grouped["pair_winrate"] = (grouped["sum"] + 1) / (grouped["count"] + 2)
    
    # Calculate standard error for confidence
    grouped["std_error"] = np.sqrt(
        grouped["pair_winrate"] * (1 - grouped["pair_winrate"]) / grouped["count"]
    )
    
    stats: dict = {}
    for key, row in grouped.iterrows():
        c1, c2 = cast(tuple[str, str], key)
        base = global_winrates.get(c1, 0.5)
        lift = row["pair_winrate"] - base
        
        # Only include if statistically significant (95% CI)
        if abs(lift) > 1.96 * row["std_error"]:
            if c1 not in stats:
                stats[c1] = {}
            stats[c1][c2] = {
                "lift": float(lift),
                "confidence": float(row["std_error"]),
                "sample_size": int(row["count"])
            }
    
    return stats
```

#### 2.2 **Memory Efficiency Issues**

**Problem**: Line 45 - Unnecessary copy
```python
mini_df = df[["champ", "allies", "win"]].copy()
```
- For large datasets, this doubles memory usage
- **Recommendation**: Use views or process in chunks

```python
def compute_synergy_memory_efficient(
    df: pd.DataFrame, 
    global_winrates: dict,
    chunk_size: int = 100_000
) -> dict:
    """Process synergy in chunks to reduce memory footprint."""
    stats: dict = {}
    
    for start_idx in range(0, len(df), chunk_size):
        chunk = df.iloc[start_idx:start_idx + chunk_size]
        chunk_stats = _compute_synergy_chunk(chunk, global_winrates)
        
        # Merge chunk stats
        for c1, c2_dict in chunk_stats.items():
            if c1 not in stats:
                stats[c1] = {}
            stats[c1].update(c2_dict)
    
    return stats
```

#### 2.3 **Data Quality Issues**

**Problem**: Line 162 - Silent failure on malformed data
```python
except Exception:
    continue  # No logging!
```

**Recommendation**: Log data quality issues
```python
malformed_count = 0
for idx, row in df.iterrows():
    try:
        blue = json.loads(row["blue_team"])
        red = json.loads(row["red_team"])
        # ... process
    except json.JSONDecodeError as e:
        malformed_count += 1
        logger.warning(f"Malformed JSON in match {row.get('match_id', 'unknown')}: {e}")
        continue
    except KeyError as e:
        malformed_count += 1
        logger.warning(f"Missing key in match {row.get('match_id', 'unknown')}: {e}")
        continue

if malformed_count > 0:
    logger.warning(f"Skipped {malformed_count} malformed matches ({malformed_count/len(df)*100:.1f}%)")
```

#### 2.4 **Missing Model Validation**

**Critical**: No validation that artifacts are reasonable

**Recommendation**: Add validation step
```python
def validate_artifacts(bundle: ArtifactBundle) -> list[str]:
    """Validate artifact quality. Returns list of warnings."""
    warnings = []
    stats = bundle.stats
    
    # Check 1: Role strength should be near 50%
    role_strength = stats.get("role_strength", {})
    for role, champs in role_strength.items():
        avg_wr = np.mean(list(champs.values()))
        if not (0.45 <= avg_wr <= 0.55):
            warnings.append(f"Role {role} avg winrate {avg_wr:.1%} is suspicious")
    
    # Check 2: Synergy/Counter lifts should be small
    synergy = stats.get("synergy", {})
    all_lifts = [lift for champ_dict in synergy.values() for lift in champ_dict.values()]
    if all_lifts:
        max_lift = max(abs(x) for x in all_lifts)
        if max_lift > 0.15:  # 15% lift is very high
            warnings.append(f"Max synergy lift {max_lift:.1%} seems too high")
    
    # Check 3: Minimum data coverage
    manifest = bundle.manifest
    if manifest.get("rows_count", 0) < 1000:
        warnings.append(f"Only {manifest['rows_count']} samples - may be unreliable")
    
    return warnings

# In build_tables():
bundle = ArtifactBundle(stats=artifacts_stats, manifest=manifest)

# Validate before saving
validation_warnings = validate_artifacts(bundle)
if validation_warnings:
    logger.warning("Artifact validation warnings:")
    for warning in validation_warnings:
        logger.warning(f"  - {warning}")

save_artifact_bundle(run_dir, bundle)
```

#### 2.5 **Missing Metrics Tracking**

**Recommendation**: Track training metrics
```python
def build_tables():
    # ... existing code ...
    
    # Track metrics
    metrics = {
        "total_matches": len(df),
        "total_participants": len(participants_df),
        "unique_champions": len(global_winrates),
        "avg_games_per_champion": len(participants_df) / len(global_winrates),
        "synergy_pairs": sum(len(v) for v in synergy.values()),
        "counter_pairs": sum(len(v) for v in counter.values()),
        "build_duration_seconds": time.time() - start_time,
    }
    
    # Add to manifest
    manifest["metrics"] = metrics
    logger.info(f"Build metrics: {json.dumps(metrics, indent=2)}")
```

---

### 3. **naive_bayes/inference.py** ⚠️ Needs Improvement

**Strengths:**
- Clean functional design
- Proper logit/sigmoid transformations
- Reasonable default handling

**Critical Issues:**

#### 3.1 **Magic Numbers**

**Problem**: Line 70 - Hardcoded scaling factor
```python
logit_scale = 4.0  # Why 4.0? No justification
```

**Recommendation**: Make configurable and document
```python
@dataclass(frozen=True)
class NaiveBayesConfig:
    role_strength_weight: float = 1.0
    synergy_weight: float = 0.5
    counter_weight: float = 0.5
    off_role_penalty: float = 0.0
    
    # New: Document the scaling rationale
    logit_scale: float = 4.0  
    # Rationale: 1% winrate diff ≈ 0.04 logit change
    # So we scale by 1/0.01 * 0.04 = 4.0 to convert % to logit
```

#### 3.2 **Incorrect Naive Bayes Implementation**

**Critical Issue**: This is NOT actually Naive Bayes!

True Naive Bayes would be:
```
P(win | champ, role, allies, enemies) ∝ 
    P(champ | role) * 
    ∏ P(ally_i | champ, win) * 
    ∏ P(enemy_j | champ, win)
```

Current implementation is an **additive lift model** (which is fine, but misnamed).

**Recommendation**: Either:
1. Rename to `additive_lift` or `linear_model`
2. Or implement true Naive Bayes

```python
# Option 1: Rename (easier)
# naive_bayes/ -> scoring/
# inference.py -> additive_lift.py

# Option 2: True Naive Bayes (more complex)
def score_candidate_naive_bayes(
    candidate: str,
    role: str,
    allies: list[str],
    enemies: list[str],
    stats: dict,
    config: NaiveBayesConfig,
) -> tuple[float, list[str]]:
    """True Naive Bayes scoring."""
    
    # P(role | champ) - from role_strength
    role_prob = _get_nested(stats.get("role_strength", {}), role, candidate, default=0.5)
    
    # P(win | champ, allies) - from synergy conditional probs
    # This requires storing P(ally | champ, win) and P(ally | champ, loss)
    # which we don't currently compute
    
    # For now, stick with additive lift but rename it
```

#### 3.3 **Missing Uncertainty Quantification**

**Problem**: Returns single point estimate, no confidence

**Recommendation**: Return confidence intervals
```python
def score_candidate(
    *,
    candidate: str,
    role: str,
    allies: list[str],
    enemies: list[str],
    stats: dict,
    config: NaiveBayesConfig,
) -> tuple[float, float, float, list[str]]:  # (score, lower_ci, upper_ci, reasons)
    """
    Returns (probability, lower_95ci, upper_95ci, reasons).
    """
    # ... existing logic ...
    
    # Estimate uncertainty from sample sizes
    role_stats = stats.get("role_strength", {}).get(role, {})
    # If we stored sample counts, we could compute proper CI
    # For now, use heuristic based on number of features
    
    n_features = 1 + len(allies) + len(enemies)
    uncertainty = 0.05 * np.sqrt(n_features)  # Rough heuristic
    
    lower_ci = max(0.0, final_prob - uncertainty)
    upper_ci = min(1.0, final_prob + uncertainty)
    
    return final_prob, lower_ci, upper_ci, reasons
```

#### 3.4 **Numerical Stability**

**Problem**: Line 22 - Clamping hides issues
```python
p = max(0.001, min(0.999, p))  # Why these specific values?
```

**Recommendation**: Use more principled approach
```python
def logit(p: float, epsilon: float = 1e-7) -> float:
    """
    Compute logit with numerical stability.
    
    Args:
        p: Probability in (0, 1)
        epsilon: Small constant to avoid log(0)
    
    Returns:
        log(p / (1-p))
    """
    p_clipped = np.clip(p, epsilon, 1 - epsilon)
    return np.log(p_clipped / (1 - p_clipped))
```

---

### 4. **naive_bayes/config.py** ✅ Good

**Strengths:**
- Clean dataclass design
- Frozen for immutability
- Reasonable defaults

**Minor Improvements:**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar

@dataclass(frozen=True)
class NaiveBayesConfig:
    """Configuration for additive lift scoring model.
    
    Attributes:
        role_strength_weight: Weight for base role winrate (typically 1.0)
        synergy_weight: Weight for ally synergy effects (0-1 range)
        counter_weight: Weight for enemy counter effects (0-1 range)
        off_role_penalty: Penalty for off-role picks (not yet implemented)
        logit_scale: Scaling factor to convert winrate lifts to logit space
    """
    role_strength_weight: float = 1.0
    synergy_weight: float = 0.5
    counter_weight: float = 0.5
    off_role_penalty: float = 0.0
    logit_scale: float = 4.0
    
    # Class-level constants for validation
    MIN_WEIGHT: ClassVar[float] = 0.0
    MAX_WEIGHT: ClassVar[float] = 2.0
    
    def __post_init__(self):
        """Validate configuration values."""
        for field_name in ["role_strength_weight", "synergy_weight", "counter_weight"]:
            value = getattr(self, field_name)
            if not (self.MIN_WEIGHT <= value <= self.MAX_WEIGHT):
                raise ValueError(f"{field_name}={value} outside valid range [{self.MIN_WEIGHT}, {self.MAX_WEIGHT}]")
```

---

## Missing Components

### 1. **Model Versioning** ❌ Critical

**Problem**: No way to track model lineage or rollback

**Recommendation**: Add versioning system
```python
# app/ml/versioning.py

from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ModelVersion:
    version: str  # e.g., "v1.2.3"
    run_id: str
    created_at: float
    metrics: dict
    config: dict
    
class ModelRegistry:
    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.versions_file = artifacts_dir / "versions.json"
    
    def register_version(self, version: ModelVersion) -> None:
        """Register a new model version."""
        versions = self._load_versions()
        versions[version.version] = {
            "run_id": version.run_id,
            "created_at": version.created_at,
            "metrics": version.metrics,
            "config": version.config,
        }
        self._save_versions(versions)
    
    def get_version(self, version: str) -> ModelVersion:
        """Load a specific version."""
        versions = self._load_versions()
        if version not in versions:
            raise ValueError(f"Version {version} not found")
        return ModelVersion(**versions[version])
    
    def list_versions(self) -> list[str]:
        """List all registered versions."""
        return list(self._load_versions().keys())
```

### 2. **Model Monitoring** ❌ Critical

**Problem**: No tracking of model performance in production

**Recommendation**: Add monitoring
```python
# app/ml/monitoring.py

from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class PredictionLog:
    timestamp: float
    model_version: str
    role: str
    top_recommendation: str
    top_score: float
    num_candidates: int
    latency_ms: float

class ModelMonitor:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_prediction(self, log: PredictionLog) -> None:
        """Log a prediction for monitoring."""
        date_str = datetime.fromtimestamp(log.timestamp).strftime("%Y-%m-%d")
        log_file = self.log_dir / f"predictions_{date_str}.jsonl"
        
        with log_file.open("a") as f:
            f.write(json.dumps(log.__dict__) + "\n")
    
    def get_daily_stats(self, date: str) -> dict:
        """Get statistics for a specific date."""
        log_file = self.log_dir / f"predictions_{date}.jsonl"
        if not log_file.exists():
            return {}
        
        logs = []
        with log_file.open() as f:
            for line in f:
                logs.append(json.loads(line))
        
        return {
            "total_predictions": len(logs),
            "avg_latency_ms": sum(log["latency_ms"] for log in logs) / len(logs),
            "avg_candidates": sum(log["num_candidates"] for log in logs) / len(logs),
            "role_distribution": self._compute_distribution(logs, "role"),
        }
```

### 3. **Feature Store** ⚠️ Nice to Have

For production systems, consider a feature store to:
- Cache computed features
- Ensure train/serve consistency
- Enable feature reuse across models

### 4. **A/B Testing Framework** ⚠️ Nice to Have

To compare model versions in production:
```python
# app/ml/ab_testing.py

class ABTestingService:
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.experiments: dict[str, dict] = {}
    
    def create_experiment(
        self, 
        name: str, 
        control_version: str, 
        treatment_version: str,
        traffic_split: float = 0.5
    ) -> None:
        """Create A/B test between two model versions."""
        self.experiments[name] = {
            "control": control_version,
            "treatment": treatment_version,
            "split": traffic_split,
        }
    
    def get_model_version(self, experiment: str, user_id: str) -> str:
        """Determine which model version to use for a user."""
        exp = self.experiments[experiment]
        # Use consistent hashing for stable assignment
        hash_val = hash(user_id) % 100
        if hash_val < exp["split"] * 100:
            return exp["treatment"]
        return exp["control"]
```

---

## Testing Gaps

### Current Test Coverage: ~60% (estimated)

**Missing Tests:**

1. **Integration tests** for full pipeline
2. **Property-based tests** (e.g., using Hypothesis)
3. **Performance benchmarks**
4. **Regression tests** with golden datasets

**Recommended Additions:**

```python
# tests/ml/test_integration.py

def test_full_pipeline_end_to_end(tmp_path):
    """Test complete flow from raw data to predictions."""
    # 1. Create synthetic match data
    # 2. Run build_tables()
    # 3. Load artifacts
    # 4. Make predictions
    # 5. Validate predictions are reasonable
    pass

# tests/ml/test_properties.py

from hypothesis import given, strategies as st

@given(
    winrate=st.floats(min_value=0.01, max_value=0.99),
    synergy_lift=st.floats(min_value=-0.1, max_value=0.1),
)
def test_score_monotonicity(winrate, synergy_lift):
    """Score should increase with positive synergy."""
    # Property: Adding positive synergy should increase score
    pass

# tests/ml/test_performance.py

import pytest

@pytest.mark.benchmark
def test_inference_latency(benchmark):
    """Ensure inference is fast enough for production."""
    def run_inference():
        score_candidate(...)
    
    result = benchmark(run_inference)
    assert result < 0.010  # 10ms SLA
```

---

## Documentation Gaps

### Missing Documentation:

1. **Model Card** - Describe model purpose, limitations, biases
2. **API Documentation** - Swagger/OpenAPI specs
3. **Runbook** - How to retrain, deploy, rollback
4. **Architecture Decision Records (ADRs)** - Why Naive Bayes? Why additive lifts?

**Recommendation**: Create `docs/ml/` directory with:

```markdown
# docs/ml/model_card.md

## Model Overview
- **Name**: Champion Recommendation Model v1
- **Type**: Additive Lift Model (misnamed as Naive Bayes)
- **Purpose**: Recommend champions based on draft state

## Training Data
- **Source**: Riot API match data
- **Size**: ~10K matches (configurable)
- **Time Period**: Last 30 days
- **Filters**: Ranked Solo/Duo, Platinum+

## Model Architecture
- **Features**:
  - Role-specific champion winrate
  - Ally synergy lifts
  - Enemy counter lifts
- **Scoring**: Logit-space additive model

## Performance
- **Offline Metrics**: N/A (no ground truth for "best pick")
- **Online Metrics**: User engagement, pick rate

## Limitations
- **Cold Start**: New champions have no data
- **Meta Shifts**: Model lags patch changes by ~1 week
- **Sample Bias**: Only high-ELO data

## Ethical Considerations
- **Fairness**: May perpetuate meta biases
- **Transparency**: Reasons provided for each recommendation
```

---

## Priority Recommendations

### P0 (Critical - Do Now)
1. ✅ **Rename "Naive Bayes"** to "Additive Lift Model" (it's not actually NB)
2. ✅ **Add artifact validation** to catch bad models before deployment
3. ✅ **Add data quality logging** in build_tables.py
4. ✅ **Add model versioning** for rollback capability

### P1 (High - Do This Sprint)
5. ✅ **Add confidence intervals** to predictions
6. ✅ **Make smoothing configurable** with better priors
7. ✅ **Add monitoring/logging** for production predictions
8. ✅ **Add integration tests** for full pipeline

### P2 (Medium - Do Next Sprint)
9. ⚠️ **Add sample size filtering** for low-confidence pairs
10. ⚠️ **Add model card documentation**
11. ⚠️ **Add performance benchmarks**
12. ⚠️ **Implement proper statistical testing** (confidence intervals, hypothesis tests)

### P3 (Nice to Have - Backlog)
13. 📋 **Feature store** for caching
14. 📋 **A/B testing framework**
15. 📋 **Hyperparameter tuning** pipeline
16. 📋 **Model explainability** (SHAP values, etc.)

---

## Code Quality Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Type Coverage | ~90% | 95% | ✅ Good |
| Test Coverage | ~60% | 80% | ⚠️ Needs Work |
| Docstring Coverage | ~40% | 80% | ❌ Poor |
| Cyclomatic Complexity | Low | <10 | ✅ Good |
| Code Duplication | Low | <5% | ✅ Good |
| Performance (p99 latency) | Unknown | <50ms | ❓ Needs Measurement |

---

## Conclusion

The current implementation is a **solid foundation** but needs hardening for production:

**Strengths:**
- Clean code structure
- Good separation of concerns
- Type hints throughout
- Basic error handling

**Weaknesses:**
- Misnamed (not actually Naive Bayes)
- Missing validation and monitoring
- Statistical rigor could be improved
- Documentation gaps
- No versioning or rollback strategy

**Recommended Next Steps:**
1. Implement P0 items (validation, versioning, renaming)
2. Add comprehensive tests
3. Document model card and runbook
4. Set up monitoring dashboard
5. Plan for A/B testing future model iterations

With these improvements, the codebase will meet senior MLE standards for a production ML system.
