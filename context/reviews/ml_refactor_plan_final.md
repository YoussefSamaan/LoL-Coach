# ML Module Refactoring Plan - FINAL (Corrected)

> **📝 Note**: For future improvements to the training pipeline (Strategy Pattern + Pipeline Pattern),
> see [`ml_training_pipeline_improvement_plan.md`](./ml_training_pipeline_improvement_plan.md).
> This refactor is **DEFERRED** until after MVP ships.

## Overview

Refactor the ML module to meet **Google SWE/SRE best practices** with corrections from peer review.

**Key Changes from v1:**
1. ✅ Fixed type definitions to match artifact structure
2. ✅ Added model registry for real rollback capability
3. ✅ Improved validation (percentile-based, not just mean)
4. ✅ Store counts with lifts for uncertainty tracking
5. ✅ Use Pydantic models instead of complex TypedDict nesting

---

## 📁 Final Structure

```
app/ml/
├── __init__.py                    # Public API exports
├── artifacts.py                   # Artifact I/O (minor updates)
├── registry.py                    # NEW: Model registry (current/previous/versions)
├── validation.py                  # NEW: Artifact validation
├── config.py                      # NEW: Centralized ML config
│
├── scoring/                       # RENAMED from naive_bayes/
│   ├── __init__.py
│   ├── config.py                 # Scoring-specific config
│   ├── inference.py              # Inference logic
│   └── models.py                 # NEW: Pydantic models for scoring
│
├── training/                      # NEW: Separate training concerns
│   ├── __init__.py
│   ├── build_tables.py           # MOVED from ml/build_tables.py
│   ├── aggregators.py            # NEW: Extract compute_* functions
│   ├── models.py                 # NEW: Pydantic models for training
│   └── config.py                 # NEW: Smoothing config
│
└── monitoring/                    # NEW: Observability
    ├── __init__.py
    └── logger.py                 # NEW: Structured logging

artifacts/
├── runs/
│   ├── 20260124_120000/
│   │   ├── stats.json
│   │   └── manifest.json
│   └── 20260124_150000/
│       ├── stats.json
│       └── manifest.json
├── registry.json                  # NEW: Current/previous pointers
└── latest.json                    # DEPRECATED: use registry instead
```

---

## 🔧 Implementation Plan

### Phase 1: Foundation with Pydantic Models (1.5 hours)

#### 1.1 Create Pydantic Models for Training [30 min]

**User Preference:** Use Pydantic models instead of TypedDict for clarity

```python
# app/ml/training/models.py

"""Pydantic models for training pipeline."""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator

# Type aliases for clarity
Role = str
Champion = str

class LiftStat(BaseModel):
    """Pairwise lift statistic with sample size.
    
    Attributes:
        lift: Winrate delta from baseline (e.g., +0.05 = +5%)
        count: Number of games this pair appeared together
    """
    lift: float = Field(..., ge=-1.0, le=1.0, description="Winrate lift")
    count: int = Field(..., gt=0, description="Sample size")
    
    class Config:
        frozen = True  # Immutable

class RoleStrengthStat(BaseModel):
    """Role-specific champion winrate.
    
    Attributes:
        winrate: Smoothed winrate for this champion in this role
        games: Number of games played
    """
    winrate: float = Field(..., ge=0.0, le=1.0)
    games: int = Field(..., gt=0)
    
    class Config:
        frozen = True

class ArtifactStats(BaseModel):
    """Complete artifact statistics structure.
    
    Stores all computed statistics from training pipeline.
    """
    # Role -> Champion -> Winrate
    role_strength: dict[Role, dict[Champion, float]]
    
    # Champion -> Ally -> {lift, count}
    synergy: dict[Champion, dict[Champion, LiftStat]]
    
    # Champion -> Enemy -> {lift, count}
    counter: dict[Champion, dict[Champion, LiftStat]]
    
    # Champion -> Global Winrate (baseline)
    global_winrates: dict[Champion, float]
    
    @field_validator('role_strength')
    @classmethod
    def validate_role_strength(cls, v):
        """Ensure all winrates are valid."""
        for role, champs in v.items():
            for champ, wr in champs.items():
                if not (0.0 <= wr <= 1.0):
                    raise ValueError(f"Invalid winrate for {role}/{champ}: {wr}")
        return v
    
    class Config:
        frozen = True

class ManifestData(BaseModel):
    """Artifact manifest metadata.
    
    Tracks provenance and configuration for reproducibility.
    """
    run_id: str
    version: str = "v1.0.0"
    timestamp: float
    rows_count: int = Field(..., gt=0)
    source: str
    
    # Configuration used for this run
    config: dict[str, object] = Field(default_factory=dict)
    
    # Data quality metrics
    data_quality: dict[str, int | float] = Field(default_factory=dict)
    
    # Artifact statistics
    artifact_stats: dict[str, int] = Field(default_factory=dict)
    
    class Config:
        frozen = True

class SmoothingConfig(BaseModel):
    """Bayesian smoothing configuration.
    
    Uses Beta(alpha, beta) prior for binomial proportions.
    - alpha = beta gives 50% prior
    - alpha + beta controls strength (equivalent sample size)
    
    Recommendations:
    - Role strength: Beta(5, 5) - moderate smoothing
    - Synergy/Counter: Beta(10, 10) - stronger smoothing for sparse pairs
    """
    role_alpha: float = Field(default=5.0, gt=0.0)
    role_beta: float = Field(default=5.0, gt=0.0)
    pair_alpha: float = Field(default=10.0, gt=0.0)
    pair_beta: float = Field(default=10.0, gt=0.0)
    min_samples: int = Field(default=5, ge=1)
    
    class Config:
        frozen = True
```

#### 1.2 Create Model Registry [30 min]

**Critical Addition:** Real rollback capability

```python
# app/ml/registry.py

"""Model registry for version management and rollback."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from app.ml.artifacts import ArtifactBundle, load_artifact_bundle
from app.utils.logger import get_logger

logger = get_logger(__name__)

class VersionInfo(BaseModel):
    """Information about a model version."""
    run_id: str
    version: str
    timestamp: float
    metrics: dict[str, int | float] = Field(default_factory=dict)
    
    class Config:
        frozen = True

class RegistryState(BaseModel):
    """Registry state tracking current and previous models."""
    current: str  # run_id
    previous: Optional[str] = None  # run_id
    versions: dict[str, VersionInfo] = Field(default_factory=dict)

class ModelRegistry:
    """Manages model versions and provides rollback capability.
    
    The registry maintains:
    - current: The active model being served
    - previous: The last known good model (for rollback)
    - versions: Map of all registered model versions
    
    Usage:
        registry = ModelRegistry(artifacts_dir)
        
        # Register new model
        registry.register(run_id, version_info)
        
        # Load current model
        bundle = registry.load_current()
        
        # Rollback to previous
        registry.rollback()
    """
    
    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.registry_file = artifacts_dir / "registry.json"
        self.runs_dir = artifacts_dir / "runs"
        
        # Ensure directories exist
        self.runs_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self) -> RegistryState:
        """Load registry state from disk."""
        if not self.registry_file.exists():
            return RegistryState(current="", previous=None, versions={})
        
        data = json.loads(self.registry_file.read_text(encoding="utf-8"))
        return RegistryState(**data)
    
    def _save_state(self, state: RegistryState) -> None:
        """Save registry state to disk."""
        self.registry_file.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8"
        )
    
    def register(
        self,
        run_id: str,
        version: str,
        metrics: dict[str, int | float]
    ) -> None:
        """Register a new model version and make it current.
        
        Args:
            run_id: Unique run identifier
            version: Semantic version (e.g., "v1.0.0")
            metrics: Training metrics for this version
        """
        state = self._load_state()
        
        # Store previous current as previous
        if state.current:
            state.previous = state.current
        
        # Add new version
        version_info = VersionInfo(
            run_id=run_id,
            version=version,
            timestamp=__import__('time').time(),
            metrics=metrics
        )
        state.versions[run_id] = version_info
        
        # Set as current
        state.current = run_id
        
        self._save_state(state)
        logger.info(
            f"Registered model version {version} (run_id={run_id}) as current",
            extra={"run_id": run_id, "version": version}
        )
    
    def load_current(self) -> ArtifactBundle:
        """Load the current model artifacts.
        
        Returns:
            ArtifactBundle for current model
            
        Raises:
            ValueError: If no current model is registered
        """
        state = self._load_state()
        if not state.current:
            raise ValueError("No current model registered")
        
        return self.load_version(state.current)
    
    def load_latest(self) -> ArtifactBundle:
        """Alias for load_current() for backward compatibility."""
        return self.load_current()
    
    def load_version(self, run_id: str) -> ArtifactBundle:
        """Load a specific model version.
        
        Args:
            run_id: Run identifier to load
            
        Returns:
            ArtifactBundle for specified version
            
        Raises:
            ValueError: If version doesn't exist
        """
        run_dir = self.runs_dir / run_id
        if not run_dir.exists():
            raise ValueError(f"Model version {run_id} not found")
        
        return load_artifact_bundle(run_dir)
    
    def rollback(self) -> None:
        """Rollback to the previous model version.
        
        Raises:
            ValueError: If no previous version exists
        """
        state = self._load_state()
        if not state.previous:
            raise ValueError("No previous model to rollback to")
        
        logger.warning(
            f"Rolling back from {state.current} to {state.previous}",
            extra={"from": state.current, "to": state.previous}
        )
        
        # Swap current and previous
        old_current = state.current
        state.current = state.previous
        state.previous = old_current
        
        self._save_state(state)
    
    def list_versions(self) -> list[VersionInfo]:
        """List all registered model versions.
        
        Returns:
            List of VersionInfo, sorted by timestamp (newest first)
        """
        state = self._load_state()
        versions = list(state.versions.values())
        versions.sort(key=lambda v: v.timestamp, reverse=True)
        return versions
    
    def get_current_version(self) -> Optional[VersionInfo]:
        """Get info about the current model version.
        
        Returns:
            VersionInfo for current model, or None if no current model
        """
        state = self._load_state()
        if not state.current:
            return None
        return state.versions.get(state.current)
```

#### 1.3 Improved Validation [30 min]

**Fixed:** Percentile-based validation, not just mean

```python
# app/ml/validation.py

"""Artifact validation for ML pipeline."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import statistics

from app.ml.artifacts import ArtifactBundle
from app.ml.training.models import LiftStat
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass(frozen=True)
class ValidationResult:
    """Result of artifact validation.
    
    Attributes:
        is_valid: Whether artifacts pass all checks
        errors: Critical issues that prevent deployment
        warnings: Non-critical issues to investigate
    """
    is_valid: bool
    errors: Sequence[str]
    warnings: Sequence[str]
    
    def log_results(self) -> None:
        """Log validation results at appropriate levels."""
        if self.errors:
            logger.error("Artifact validation FAILED:")
            for error in self.errors:
                logger.error(f"  ERROR: {error}")
        
        if self.warnings:
            logger.warning("Artifact validation warnings:")
            for warning in self.warnings:
                logger.warning(f"  WARNING: {warning}")
        
        if self.is_valid and not self.warnings:
            logger.info("Artifact validation PASSED")

class ArtifactValidator:
    """Validates ML artifacts before deployment.
    
    Implements cheap sanity checks to catch pipeline failures:
    1. Structure validation (required keys exist)
    2. Range validation (winrates in [0,1])
    3. Distribution validation (percentiles, not just mean)
    4. Coverage validation (enough data)
    5. Sanity validation (lifts not extreme)
    """
    
    # Thresholds (configurable)
    MIN_WINRATE = 0.0
    MAX_WINRATE = 1.0
    
    # Percentile-based checks (more robust than mean)
    MIN_P5_WINRATE = 0.35   # 5th percentile shouldn't be too low
    MAX_P95_WINRATE = 0.65  # 95th percentile shouldn't be too high
    
    MAX_ABS_LIFT_P99 = 0.20  # 99th percentile lift < 20%
    
    MIN_ROWS_ERROR = 100
    MIN_ROWS_WARNING = 1000
    MIN_CHAMPIONS = 50
    MIN_ROLE_COVERAGE = 4  # At least 4 roles should have data
    
    def validate(self, bundle: ArtifactBundle) -> ValidationResult:
        """Run all validation checks.
        
        Args:
            bundle: Artifact bundle to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors: list[str] = []
        warnings: list[str] = []
        
        # Check 1: Structure
        errors.extend(self._validate_structure(bundle.stats))
        
        if errors:
            # If structure is broken, can't run other checks
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Check 2-5: Content validation
        warnings.extend(self._validate_winrates(bundle.stats))
        warnings.extend(self._validate_lifts(bundle.stats))
        errors.extend(self._validate_coverage(bundle))
        warnings.extend(self._validate_role_coverage(bundle.stats))
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
    
    def _validate_structure(self, stats: dict) -> list[str]:
        """Validate required keys exist."""
        errors = []
        required_keys = ["role_strength", "synergy", "counter", "global_winrates"]
        
        for key in required_keys:
            if key not in stats:
                errors.append(f"Missing required stat: {key}")
        
        return errors
    
    def _validate_winrates(self, stats: dict) -> list[str]:
        """Validate winrate ranges and distribution using percentiles."""
        warnings = []
        role_strength = stats["role_strength"]
        
        all_winrates = []
        for role, champs in role_strength.items():
            if not champs:
                warnings.append(f"Role {role} has no champions")
                continue
            
            for champ, wr in champs.items():
                if not (self.MIN_WINRATE <= wr <= self.MAX_WINRATE):
                    warnings.append(f"Invalid winrate for {role}/{champ}: {wr:.3f}")
                all_winrates.append(wr)
        
        if len(all_winrates) >= 10:  # Need enough data for percentiles
            # Use percentiles instead of mean (more robust)
            sorted_wr = sorted(all_winrates)
            p5 = sorted_wr[len(sorted_wr) // 20]  # 5th percentile
            p95 = sorted_wr[(len(sorted_wr) * 19) // 20]  # 95th percentile
            median = statistics.median(all_winrates)
            
            if p5 < self.MIN_P5_WINRATE:
                warnings.append(
                    f"5th percentile winrate {p5:.1%} is very low "
                    f"(expected >{self.MIN_P5_WINRATE:.0%})"
                )
            
            if p95 > self.MAX_P95_WINRATE:
                warnings.append(
                    f"95th percentile winrate {p95:.1%} is very high "
                    f"(expected <{self.MAX_P95_WINRATE:.0%})"
                )
            
            # Log distribution for debugging
            logger.info(
                f"Winrate distribution: p5={p5:.1%}, median={median:.1%}, p95={p95:.1%}"
            )
        
        return warnings
    
    def _validate_lifts(self, stats: dict) -> list[str]:
        """Validate lift magnitudes using percentiles."""
        warnings = []
        
        all_lifts = []
        
        # Extract lifts from synergy/counter
        for champ_dict in stats["synergy"].values():
            for lift_data in champ_dict.values():
                if isinstance(lift_data, dict):
                    all_lifts.append(lift_data["lift"])
                else:
                    all_lifts.append(lift_data)  # Backward compat
        
        for champ_dict in stats["counter"].values():
            for lift_data in champ_dict.values():
                if isinstance(lift_data, dict):
                    all_lifts.append(lift_data["lift"])
                else:
                    all_lifts.append(lift_data)
        
        if len(all_lifts) >= 10:
            abs_lifts = [abs(x) for x in all_lifts]
            sorted_abs = sorted(abs_lifts)
            p99 = sorted_abs[(len(sorted_abs) * 99) // 100]  # 99th percentile
            
            if p99 > self.MAX_ABS_LIFT_P99:
                warnings.append(
                    f"99th percentile absolute lift {p99:.1%} exceeds threshold "
                    f"{self.MAX_ABS_LIFT_P99:.0%} - may indicate data issue"
                )
            
            logger.info(f"Lift distribution: p99_abs={p99:.1%}")
        
        return warnings
    
    def _validate_coverage(self, bundle: ArtifactBundle) -> list[str]:
        """Validate sufficient data coverage."""
        errors = []
        
        rows_count = bundle.manifest.get("rows_count", 0)
        if rows_count < self.MIN_ROWS_ERROR:
            errors.append(
                f"Only {rows_count} participant rows - "
                f"minimum {self.MIN_ROWS_ERROR} required"
            )
        elif rows_count < self.MIN_ROWS_WARNING:
            # This is a warning, not error
            pass
        
        num_champs = len(bundle.stats["global_winrates"])
        if num_champs < self.MIN_CHAMPIONS:
            errors.append(
                f"Only {num_champs} champions - "
                f"minimum {self.MIN_CHAMPIONS} required for production"
            )
        
        return errors
    
    def _validate_role_coverage(self, stats: dict) -> list[str]:
        """Validate coverage across roles."""
        warnings = []
        
        role_strength = stats["role_strength"]
        num_roles = len(role_strength)
        
        if num_roles < self.MIN_ROLE_COVERAGE:
            warnings.append(
                f"Only {num_roles} roles have data - "
                f"expected at least {self.MIN_ROLE_COVERAGE}"
            )
        
        return warnings


def validate_artifacts(bundle: ArtifactBundle) -> ValidationResult:
    """Convenience function for validation.
    
    Args:
        bundle: Artifact bundle to validate
        
    Returns:
        ValidationResult
    """
    validator = ArtifactValidator()
    return validator.validate(bundle)
```

#### 1.4 Structured Logging (Fixed) [10 min]

**Fixed:** Ensure compatibility with logger

```python
# app/ml/monitoring/logger.py

"""Structured logging for ML pipeline."""

from __future__ import annotations
import time
import json
from contextlib import contextmanager
from typing import Any, Iterator

from app.utils.logger import get_logger

logger = get_logger(__name__)

class MLLogger:
    """Structured logger for ML operations.
    
    Provides consistent logging format with timing and metadata.
    Handles both structured (extra=) and JSON-in-message logging.
    """
    
    @staticmethod
    @contextmanager
    def log_operation(
        operation: str,
        **metadata: Any
    ) -> Iterator[dict[str, Any]]:
        """Context manager for logging operations with timing.
        
        Usage:
            with MLLogger.log_operation("build_tables", patch="14.1") as ctx:
                # ... do work ...
                ctx["rows_processed"] = 1000
        
        Args:
            operation: Name of the operation
            **metadata: Additional metadata to log
            
        Yields:
            Mutable dict for adding result metadata
        """
        start_time = time.time()
        
        # Log start with metadata as JSON (ensures it's always visible)
        start_msg = f"Starting {operation}"
        if metadata:
            start_msg += f" | {json.dumps(metadata)}"
        logger.info(start_msg)
        
        result_metadata: dict[str, Any] = {}
        
        try:
            yield result_metadata
            
            duration = time.time() - start_time
            all_metadata = {
                **metadata,
                **result_metadata,
                "duration_seconds": round(duration, 3),
                "status": "success"
            }
            
            end_msg = f"Completed {operation} | {json.dumps(all_metadata)}"
            logger.info(end_msg)
            
        except Exception as e:
            duration = time.time() - start_time
            error_metadata = {
                **metadata,
                "duration_seconds": round(duration, 3),
                "status": "error",
                "error": str(e)
            }
            
            error_msg = f"Failed {operation} | {json.dumps(error_metadata)}"
            logger.error(error_msg, exc_info=True)
            raise
```

---

### Phase 2: Refactor Training with Counts (1.5 hours)

#### 2.1 Update Aggregators to Store Counts [45 min]

**Critical Fix:** Store lift + count together

```python
# app/ml/training/aggregators.py

"""Statistical aggregators for match data."""

from __future__ import annotations
from typing import cast

import pandas as pd

from app.ml.training.models import LiftStat, SmoothingConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RoleStrengthAggregator:
    """Computes role-specific champion winrates."""
    
    def __init__(self, config: SmoothingConfig):
        self.config = config
    
    def compute(self, df: pd.DataFrame) -> dict[str, dict[str, float]]:
        """Compute role strength (winrate) for each champion in each role.
        
        Args:
            df: DataFrame with columns [target_role, champ, win]
            
        Returns:
            Nested dict: {role: {champion: winrate}}
        """
        grouped = df.groupby(["target_role", "champ"])["win"].agg(["sum", "count"])
        
        # Apply Bayesian smoothing
        grouped["winrate"] = (
            (grouped["sum"] + self.config.role_alpha) /
            (grouped["count"] + self.config.role_alpha + self.config.role_beta)
        )
        
        stats: dict[str, dict[str, float]] = {}
        for key, row in grouped.iterrows():
            role, champ = cast(tuple[str, str], key)
            if role not in stats:
                stats[role] = {}
            stats[role][champ] = float(row["winrate"])
        
        logger.info(
            f"Computed role strength for {len(stats)} roles, "
            f"{sum(len(v) for v in stats.values())} champion-role pairs"
        )
        
        return stats

class SynergyAggregator:
    """Computes ally synergy lifts."""
    
    def __init__(self, config: SmoothingConfig):
        self.config = config
    
    def compute(
        self,
        df: pd.DataFrame,
        global_winrates: dict[str, float]
    ) -> dict[str, dict[str, LiftStat]]:
        """Compute synergy lift for champion pairs.
        
        Args:
            df: DataFrame with columns [champ, allies, win]
            global_winrates: Baseline winrates per champion
            
        Returns:
            Nested dict: {champion: {ally: LiftStat(lift, count)}}
        """
        mini_df = df[["champ", "allies", "win"]].copy()
        exploded = mini_df.explode("allies")
        
        grouped = exploded.groupby(["champ", "allies"])["win"].agg(["sum", "count"])
        
        # Filter low-sample pairs
        grouped = grouped[grouped["count"] >= self.config.min_samples]
        
        # Apply smoothing
        grouped["pair_winrate"] = (
            (grouped["sum"] + self.config.pair_alpha) /
            (grouped["count"] + self.config.pair_alpha + self.config.pair_beta)
        )
        
        stats: dict[str, dict[str, LiftStat]] = {}
        
        for key, row in grouped.iterrows():
            c1, c2 = cast(tuple[str, str], key)
            base = global_winrates.get(c1, 0.5)
            lift = row["pair_winrate"] - base
            
            if c1 not in stats:
                stats[c1] = {}
            
            # Store lift + count as LiftStat
            stats[c1][c2] = LiftStat(
                lift=float(lift),
                count=int(row["count"])
            )
        
        total_pairs = sum(len(v) for v in stats.values())
        logger.info(
            f"Computed synergy for {total_pairs} champion pairs "
            f"(min_samples={self.config.min_samples})"
        )
        
        return stats

class CounterAggregator:
    """Computes enemy counter lifts."""
    
    def __init__(self, config: SmoothingConfig):
        self.config = config
    
    def compute(
        self,
        df: pd.DataFrame,
        global_winrates: dict[str, float]
    ) -> dict[str, dict[str, LiftStat]]:
        """Compute counter lift for champion matchups.
        
        Args:
            df: DataFrame with columns [champ, enemies, win]
            global_winrates: Baseline winrates per champion
            
        Returns:
            Nested dict: {champion: {enemy: LiftStat(lift, count)}}
        """
        mini_df = df[["champ", "enemies", "win"]].copy()
        exploded = mini_df.explode("enemies")
        
        grouped = exploded.groupby(["champ", "enemies"])["win"].agg(["sum", "count"])
        
        # Filter low-sample pairs
        grouped = grouped[grouped["count"] >= self.config.min_samples]
        
        # Apply smoothing
        grouped["matchup_winrate"] = (
            (grouped["sum"] + self.config.pair_alpha) /
            (grouped["count"] + self.config.pair_alpha + self.config.pair_beta)
        )
        
        stats: dict[str, dict[str, LiftStat]] = {}
        
        for key, row in grouped.iterrows():
            cand, enemy = cast(tuple[str, str], key)
            base = global_winrates.get(cand, 0.5)
            lift = row["matchup_winrate"] - base
            
            if cand not in stats:
                stats[cand] = {}
            
            # Store lift + count as LiftStat
            stats[cand][enemy] = LiftStat(
                lift=float(lift),
                count=int(row["count"])
            )
        
        total_pairs = sum(len(v) for v in stats.values())
        logger.info(
            f"Computed counter for {total_pairs} champion matchups "
            f"(min_samples={self.config.min_samples})"
        )
        
        return stats
```

#### 2.2 Refactor build_tables.py [45 min]

Move to `app/ml/training/build_tables.py` with all improvements:
- Use aggregator classes
- Store counts with lifts
- Add structured logging
- Add validation
- Better error handling
- Register with model registry

---

### Phase 3: Update Scoring & Integration (45 min)

#### 3.1 Rename and Update Inference [30 min]

- Rename `naive_bayes/` → `scoring/`
- Update inference to handle LiftStat (extract .lift)
- Update config with documentation
- Add Pydantic models

#### 3.2 Update Service Integration [15 min]

- Update `recommend_service.py` to use ModelRegistry
- Update imports
- Handle LiftStat in stats

---

### Phase 4: Documentation & Testing (30 min)

#### 4.1 Add Comprehensive Docstrings [15 min]

Google-style docstrings on all public APIs.

#### 4.2 Update Tests [15 min]

- Update tests for new structure
- Add tests for registry
- Add tests for validation
- Ensure >90% coverage

---

## 📊 Success Criteria

After refactoring:

### Code Quality
- ✅ Pydantic models for all data structures (no complex TypedDict)
- ✅ Type hints on all public APIs
- ✅ Google-style docstrings everywhere
- ✅ Single Responsibility Principle

### Reliability
- ✅ Model registry with real rollback
- ✅ Percentile-based validation (robust)
- ✅ Counts stored with lifts (uncertainty tracking)
- ✅ Structured error handling

### Observability
- ✅ Structured logging (JSON-compatible)
- ✅ Clear error messages
- ✅ Metrics in manifest

---

## 📅 Timeline

| Phase | Time | Tasks |
|-------|------|-------|
| Phase 1: Foundation | 1.5h | Pydantic models, registry, validation, logging |
| Phase 2: Training | 1.5h | Aggregators with counts, refactor build_tables |
| Phase 3: Scoring | 45min | Rename, update inference, integration |
| Phase 4: Docs & Tests | 30min | Docstrings, update tests |
| **Total** | **4h 15min** | Full refactor to senior standards |

---

## ✅ Ready to Execute

This plan addresses all peer review feedback:

1. ✅ **Fixed types** - Pydantic models, LiftStat stores lift+count
2. ✅ **Added registry** - Real rollback capability
3. ✅ **Improved validation** - Percentile-based, not just mean
4. ✅ **Fixed logging** - JSON-in-message for compatibility
5. ✅ **User preference** - Pydantic models instead of complex TypedDict

**Shall I proceed with implementation?**
