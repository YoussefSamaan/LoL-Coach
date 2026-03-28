# ML Training Pipeline - Future Improvement Plan

## Status: DEFERRED (Post-MVP)

**Current State**: `build_tables.py` is functional, well-documented, and good enough for MVP.

**Decision**: Ship the current implementation with 100% test coverage, then refactor later for better maintainability and extensibility.

---

## Current Implementation (MVP)

### Structure
```
app/ml/
├── build_tables.py              # Monolithic training script (358 lines)
├── training/
│   ├── __init__.py
│   └── models.py                # Pydantic models
```

### What Works Well
✅ Clear, linear flow that's easy to follow  
✅ Well-documented with docstrings  
✅ Proper error handling  
✅ Pydantic validation for data integrity  
✅ Reasonable file size (358 lines)  

### Known Limitations
⚠️ Mixed concerns (I/O, computation, orchestration in one file)  
⚠️ Hard to unit test individual steps in isolation  
⚠️ Aggregator functions are tightly coupled to the main flow  
⚠️ Adding new statistics requires modifying the main function  
⚠️ No easy way to run partial pipelines (e.g., skip validation)  

---

## Future Improvement: Pipeline Pattern

### Goals
1. **Separation of Concerns**: Each component has a single responsibility
2. **Testability**: Each step can be tested independently
3. **Extensibility**: Easy to add new aggregators or steps
4. **Reusability**: Aggregators can be used outside the pipeline
5. **Observability**: Better logging and monitoring at each step
6. **Flexibility**: Easy to compose different pipelines for different use cases

---

## Proposed Architecture

### Directory Structure
```
app/ml/training/
├── __init__.py                  # Public API exports
├── models.py                    # Pydantic models (EXISTING)
├── config.py                    # Training configuration
├── pipeline.py                  # TrainingPipeline orchestrator
├── context.py                   # TrainingContext (shared state)
│
├── aggregators/                 # Strategy Pattern for statistics
│   ├── __init__.py
│   ├── base.py                 # BaseAggregator ABC
│   ├── role_strength.py        # RoleStrengthAggregator
│   ├── synergy.py              # SynergyAggregator
│   ├── counter.py              # CounterAggregator
│   └── baseline.py             # BaselineAggregator (global winrates)
│
├── steps/                       # Pipeline Steps
│   ├── __init__.py
│   ├── load_data.py            # LoadDataStep
│   ├── transform.py            # TransformToParticipantsStep
│   ├── compute_stats.py        # ComputeStatsStep
│   ├── validate.py             # ValidateArtifactsStep
│   └── save.py                 # SaveArtifactsStep
│
└── main.py                      # CLI entry point
```

---

## Detailed Design

### 1. TrainingContext (Shared State)

Similar to `PipelineContext` in ingest, but tailored for training.

```python
# app/ml/training/context.py

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import pandas as pd

from app.ml.training.models import ArtifactStats, ManifestData, SmoothingConfig

@dataclass
class TrainingContext:
    """Shared state for training pipeline.
    
    Attributes:
        run_id: Unique identifier for this training run
        config: Smoothing and training configuration
        state: Key-value store for passing data between steps
    """
    run_id: str
    config: SmoothingConfig
    state: dict[str, Any] = field(default_factory=dict)
    
    # Commonly accessed state (with type hints for IDE support)
    
    @property
    def raw_df(self) -> pd.DataFrame | None:
        """Raw match data loaded from parquet."""
        return self.state.get("raw_df")
    
    @raw_df.setter
    def raw_df(self, value: pd.DataFrame) -> None:
        self.state["raw_df"] = value
    
    @property
    def participants_df(self) -> pd.DataFrame | None:
        """Transformed participant-level data."""
        return self.state.get("participants_df")
    
    @participants_df.setter
    def participants_df(self, value: pd.DataFrame) -> None:
        self.state["participants_df"] = value
    
    @property
    def global_winrates(self) -> dict[str, float] | None:
        """Baseline winrates per champion."""
        return self.state.get("global_winrates")
    
    @global_winrates.setter
    def global_winrates(self, value: dict[str, float]) -> None:
        self.state["global_winrates"] = value
    
    @property
    def artifact_stats(self) -> ArtifactStats | None:
        """Computed artifact statistics."""
        return self.state.get("artifact_stats")
    
    @artifact_stats.setter
    def artifact_stats(self, value: ArtifactStats) -> None:
        self.state["artifact_stats"] = value
    
    @property
    def manifest(self) -> ManifestData | None:
        """Artifact manifest metadata."""
        return self.state.get("manifest")
    
    @manifest.setter
    def manifest(self, value: ManifestData) -> None:
        self.state["manifest"] = value
```

**Benefits**:
- Type-safe access to common state
- Clear contract for what data flows between steps
- Easy to debug (can inspect context at any point)

---

### 2. BaseAggregator (Strategy Pattern)

Abstract base class for all statistical aggregators.

```python
# app/ml/training/aggregators/base.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from app.ml.training.models import SmoothingConfig

class BaseAggregator(ABC):
    """Base class for statistical aggregators.
    
    Each aggregator computes one type of statistic from match data.
    Subclasses must implement the `compute()` method.
    """
    
    def __init__(self, config: SmoothingConfig):
        self.config = config
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging."""
        pass
    
    @abstractmethod
    def compute(self, df: pd.DataFrame, **kwargs: Any) -> Any:
        """Compute statistics from the input DataFrame.
        
        Args:
            df: Input DataFrame (usually participants_df)
            **kwargs: Additional context (e.g., global_winrates)
            
        Returns:
            Computed statistics (type varies by aggregator)
        """
        pass
    
    def validate_input(self, df: pd.DataFrame, required_columns: list[str]) -> None:
        """Validate that required columns exist.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            
        Raises:
            ValueError: If any required column is missing
        """
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(
                f"{self.name} requires columns {required_columns}, "
                f"but missing: {missing}"
            )
```

**Benefits**:
- Enforces consistent interface
- Reusable validation logic
- Easy to add new aggregators

---

### 3. Concrete Aggregators

Each aggregator is a focused, testable class.

```python
# app/ml/training/aggregators/role_strength.py

from __future__ import annotations
from typing import cast

import pandas as pd

from app.ml.training.aggregators.base import BaseAggregator
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RoleStrengthAggregator(BaseAggregator):
    """Computes role-specific champion winrates."""
    
    @property
    def name(self) -> str:
        return "Role Strength"
    
    def compute(self, df: pd.DataFrame, **kwargs) -> dict[str, dict[str, float]]:
        """Compute role strength (winrate) for each champion in each role.
        
        Args:
            df: DataFrame with columns [target_role, champ, win]
            
        Returns:
            Nested dict: {role: {champion: winrate}}
        """
        self.validate_input(df, ["target_role", "champ", "win"])
        
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
```

```python
# app/ml/training/aggregators/synergy.py

from __future__ import annotations
from typing import cast

import pandas as pd

from app.ml.training.aggregators.base import BaseAggregator
from app.ml.training.models import LiftStat
from app.utils.logger import get_logger

logger = get_logger(__name__)

class SynergyAggregator(BaseAggregator):
    """Computes ally synergy lifts."""
    
    @property
    def name(self) -> str:
        return "Synergy"
    
    def compute(
        self,
        df: pd.DataFrame,
        global_winrates: dict[str, float],
        **kwargs
    ) -> dict[str, dict[str, LiftStat]]:
        """Compute synergy lift for champion pairs.
        
        Args:
            df: DataFrame with columns [champ, allies, win]
            global_winrates: Baseline winrates per champion
            
        Returns:
            Nested dict: {champion: {ally: LiftStat(lift, count)}}
        """
        self.validate_input(df, ["champ", "allies", "win"])
        
        # Explode allies list
        mini_df = df[["champ", "allies", "win"]].copy()
        exploded = mini_df.explode("allies").dropna(subset=["allies"])
        
        # Group by (champ, ally)
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
            champ, ally = cast(tuple[str, str], key)
            count = int(row["count"])
            
            # Compute lift from baseline
            base = global_winrates.get(champ, 0.5)
            lift = float(row["pair_winrate"] - base)
            lift = max(-1.0, min(1.0, lift))  # Clamp
            
            if champ not in stats:
                stats[champ] = {}
            stats[champ][ally] = LiftStat(lift=lift, count=count)
        
        total_pairs = sum(len(allies) for allies in stats.values())
        logger.info(f"Computed {total_pairs} synergy pairs")
        
        return stats
```

**Similar pattern for**:
- `CounterAggregator` (app/ml/training/aggregators/counter.py)
- `BaselineAggregator` (app/ml/training/aggregators/baseline.py)

---

### 4. Pipeline Steps

Each step is a focused unit of work.

```python
# app/ml/training/steps/load_data.py

from __future__ import annotations

import pandas as pd

from app.config.settings import settings
from app.ml.training.pipeline import TrainingStep
from app.ml.training.context import TrainingContext
from app.utils.logger import get_logger

logger = get_logger(__name__)

class LoadDataStep(TrainingStep):
    """Load parsed match data from parquet."""
    
    name = "Load Data"
    
    def run(self, context: TrainingContext) -> None:
        parsed_dir = settings.data_root / settings.ingest.paths.parsed_dir
        
        if not parsed_dir.exists():
            raise FileNotFoundError(f"Parsed data directory not found: {parsed_dir}")
        
        logger.info(f"Loading data from {parsed_dir}")
        df = pd.read_parquet(parsed_dir)
        
        if df.empty:
            raise ValueError("Loaded DataFrame is empty - no data to process")
        
        logger.info(f"Loaded {len(df)} match records")
        context.raw_df = df
```

```python
# app/ml/training/steps/transform.py

from __future__ import annotations

import json
import pandas as pd

from app.ml.training.pipeline import TrainingStep
from app.ml.training.context import TrainingContext
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TransformToParticipantsStep(TrainingStep):
    """Transform match-level data to participant-level data."""
    
    name = "Transform to Participants"
    
    def run(self, context: TrainingContext) -> None:
        df = context.raw_df
        if df is None:
            raise ValueError("raw_df not found in context")
        
        participants = []
        malformed_count = 0
        
        for _, row in df.iterrows():
            try:
                blue = json.loads(row["blue_team"])
                red = json.loads(row["red_team"])
                winner = row["winner"]
                
                # Blue participants
                for p in blue:
                    others = [x["c"] for x in blue if x["c"] != p["c"]]
                    enemies = [x["c"] for x in red]
                    participants.append({
                        "match_id": row["match_id"],
                        "champ": p["c"],
                        "target_role": p["r"].upper(),
                        "win": (winner == "BLUE"),
                        "allies": others,
                        "enemies": enemies,
                    })
                
                # Red participants
                for p in red:
                    others = [x["c"] for x in red if x["c"] != p["c"]]
                    enemies = [x["c"] for x in blue]
                    participants.append({
                        "match_id": row["match_id"],
                        "champ": p["c"],
                        "target_role": p["r"].upper(),
                        "win": (winner == "RED"),
                        "allies": others,
                        "enemies": enemies,
                    })
            except Exception:
                malformed_count += 1
                continue
        
        if not participants:
            raise ValueError("No valid participants extracted from matches")
        
        participants_df = pd.DataFrame(participants)
        logger.info(
            f"Expanded to {len(participants_df)} participant rows "
            f"({malformed_count} malformed matches skipped)"
        )
        
        context.participants_df = participants_df
        context.state["malformed_count"] = malformed_count
```

```python
# app/ml/training/steps/compute_stats.py

from __future__ import annotations

from app.ml.training.pipeline import TrainingStep
from app.ml.training.context import TrainingContext
from app.ml.training.aggregators import (
    BaselineAggregator,
    RoleStrengthAggregator,
    SynergyAggregator,
    CounterAggregator,
)
from app.ml.training.models import ArtifactStats
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ComputeStatsStep(TrainingStep):
    """Compute all statistics using aggregators."""
    
    name = "Compute Statistics"
    
    def run(self, context: TrainingContext) -> None:
        df = context.participants_df
        if df is None:
            raise ValueError("participants_df not found in context")
        
        # 1. Compute baseline (global winrates)
        logger.info("Computing global winrates...")
        baseline_agg = BaselineAggregator(context.config)
        global_winrates = baseline_agg.compute(df)
        context.global_winrates = global_winrates
        
        # 2. Compute role strength
        logger.info("Computing role strength...")
        role_agg = RoleStrengthAggregator(context.config)
        role_strength = role_agg.compute(df)
        
        # 3. Compute synergy
        logger.info("Computing synergy...")
        synergy_agg = SynergyAggregator(context.config)
        synergy = synergy_agg.compute(df, global_winrates=global_winrates)
        
        # 4. Compute counter
        logger.info("Computing counter...")
        counter_agg = CounterAggregator(context.config)
        counter = counter_agg.compute(df, global_winrates=global_winrates)
        
        # 5. Create validated artifact stats
        stats = ArtifactStats(
            role_strength=role_strength,
            synergy=synergy,
            counter=counter,
            global_winrates=global_winrates,
        )
        
        context.artifact_stats = stats
        
        # Store metrics for manifest
        synergy_pairs = sum(len(allies) for allies in synergy.values())
        counter_pairs = sum(len(enemies) for enemies in counter.values())
        context.state["synergy_pairs"] = synergy_pairs
        context.state["counter_pairs"] = counter_pairs
        
        logger.info(
            f"Generated {synergy_pairs} synergy pairs, {counter_pairs} counter pairs"
        )
```

**Similar pattern for**:
- `ValidateArtifactsStep` (uses existing `ArtifactValidator`)
- `SaveArtifactsStep` (saves bundle + updates registry)

---

### 5. TrainingPipeline (Orchestrator)

```python
# app/ml/training/pipeline.py

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ml.training.context import TrainingContext
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TrainingStep(ABC):
    """Base class for training pipeline steps."""
    
    name: str = "BaseStep"
    
    @abstractmethod
    def run(self, context: TrainingContext) -> None:
        """Execute this step.
        
        Args:
            context: Shared training context
            
        Raises:
            Exception: If step fails
        """
        pass

class TrainingPipeline:
    """Orchestrates the training pipeline."""
    
    def __init__(self) -> None:
        self.steps: list[TrainingStep] = []
    
    def add_step(self, step: TrainingStep) -> TrainingPipeline:
        """Add a step to the pipeline."""
        self.steps.append(step)
        return self
    
    def remove_step_by_name(self, name: str) -> TrainingPipeline:
        """Remove a step by name."""
        self.steps = [s for s in self.steps if s.name != name]
        return self
    
    def execute(self, context: TrainingContext) -> None:
        """Execute all steps in order.
        
        Args:
            context: Training context
            
        Raises:
            Exception: If any step fails
        """
        logger.info(f"=== Training Pipeline Start: {context.run_id} ===")
        
        for step in self.steps:
            logger.info(f">> Step: {step.name}")
            try:
                step.run(context)
            except Exception as e:
                logger.error(f"!! Failed at {step.name}: {e}")
                raise
        
        logger.info("=== Training Pipeline Complete ===")
```

---

### 6. Main Entry Point

```python
# app/ml/training/main.py

from __future__ import annotations

import argparse
from datetime import datetime

from app.ml.training.pipeline import TrainingPipeline
from app.ml.training.context import TrainingContext
from app.ml.training.models import SmoothingConfig
from app.ml.training.steps import (
    LoadDataStep,
    TransformToParticipantsStep,
    ComputeStatsStep,
    ValidateArtifactsStep,
    SaveArtifactsStep,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

def main() -> int:
    """Run the training pipeline."""
    parser = argparse.ArgumentParser(description="ML Training Pipeline")
    parser.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="Minimum samples for synergy/counter pairs"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip artifact validation (not recommended)"
    )
    args = parser.parse_args()
    
    # Create configuration
    config = SmoothingConfig(min_samples=args.min_samples)
    
    # Create context
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    context = TrainingContext(run_id=run_id, config=config)
    
    # Build pipeline
    pipeline = TrainingPipeline()
    pipeline.add_step(LoadDataStep())
    pipeline.add_step(TransformToParticipantsStep())
    pipeline.add_step(ComputeStatsStep())
    
    if not args.skip_validation:
        pipeline.add_step(ValidateArtifactsStep())
    
    pipeline.add_step(SaveArtifactsStep())
    
    # Execute
    try:
        pipeline.execute(context)
        logger.info(f"Training complete! Run ID: {run_id}")
        return 0
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Migration Strategy

When ready to implement this refactor:

### Phase 1: Extract Aggregators (Low Risk)
1. Create `aggregators/` directory
2. Move `compute_role_strength`, `compute_synergy`, `compute_counter` to aggregator classes
3. Update `build_tables.py` to use aggregator classes
4. Ensure all tests pass
5. Commit: "refactor: extract aggregators into strategy pattern"

### Phase 2: Create Pipeline (Medium Risk)
1. Create `pipeline.py` and `context.py`
2. Create `steps/` directory with initial steps
3. Keep both `build_tables.py` and new pipeline working side-by-side
4. Add tests for new pipeline
5. Commit: "feat: add training pipeline (parallel to build_tables)"

### Phase 3: Switch Over (Low Risk)
1. Update all references to use new pipeline
2. Deprecate `build_tables.py` (keep for reference)
3. Ensure 100% test coverage
4. Commit: "refactor: switch to training pipeline"

### Phase 4: Cleanup (Low Risk)
1. Remove `build_tables.py`
2. Update documentation
3. Commit: "chore: remove deprecated build_tables.py"

---

## Testing Strategy

### Unit Tests
- Each aggregator tested independently
- Each step tested with mocked context
- Pipeline orchestration tested with mocked steps

### Integration Tests
- End-to-end pipeline with real data
- Validation that output matches current implementation

### Test Coverage Goal
- 100% line coverage for all new code
- Maintain existing coverage for unchanged code

---

## Benefits Summary

### Immediate Benefits (Phase 1)
✅ Aggregators are reusable  
✅ Easier to test individual computations  
✅ Clear separation of statistical logic  

### Medium-term Benefits (Phase 2-3)
✅ Steps can be tested independently  
✅ Easy to add new steps (e.g., feature engineering)  
✅ Better observability (logging per step)  
✅ Flexible pipeline composition  

### Long-term Benefits
✅ Easy to add new aggregators (e.g., team composition stats)  
✅ Can create different pipelines for different use cases  
✅ Better foundation for MLOps (versioning, monitoring)  
✅ Easier onboarding for new developers  

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Over-engineering for current needs | Defer until MVP is shipped and validated |
| Breaking existing functionality | Keep old implementation until new one is fully tested |
| Increased complexity | Thorough documentation and clear naming |
| Migration takes too long | Phase the migration, ship incrementally |

---

## Decision: DEFER

**Rationale**: Current implementation is good enough for MVP. Focus on:
1. ✅ Achieving 100% test coverage on current code
2. ✅ Shipping the MVP
3. ✅ Validating the approach with real users
4. ⏸️ Refactor later when we have more data on what flexibility we actually need

**Review Date**: After M1 is shipped and stable.

---

## References

- Current implementation: `backend/app/ml/build_tables.py`
- Ingest pipeline pattern: `backend/app/ingest/pipeline.py`
- ML refactor plan: `context/ml_refactor_plan_final.md`
