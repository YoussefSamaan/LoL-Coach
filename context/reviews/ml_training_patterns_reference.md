# Quick Reference: Training Pipeline Patterns

## Current (MVP) vs Future (Improved)

### Current: Monolithic Function
```python
# app/ml/build_tables.py

def build_tables(config):
    # 1. Load data
    df = pd.read_parquet(parsed_dir)
    
    # 2. Transform
    participants = transform_to_participants(df)
    
    # 3. Compute stats
    global_winrates = compute_global_winrates(participants)
    role_strength = compute_role_strength(participants, config)
    synergy = compute_synergy(participants, global_winrates, config)
    counter = compute_counter(participants, global_winrates, config)
    
    # 4. Validate & Save
    stats = ArtifactStats(...)
    save_artifact_bundle(run_dir, bundle)
```

**Pros**: Simple, linear, easy to follow  
**Cons**: Hard to test steps independently, tight coupling

---

### Future: Pipeline + Strategy Pattern
```python
# app/ml/training/main.py

def main():
    context = TrainingContext(run_id=run_id, config=config)
    
    pipeline = TrainingPipeline()
    pipeline.add_step(LoadDataStep())
    pipeline.add_step(TransformToParticipantsStep())
    pipeline.add_step(ComputeStatsStep())  # Uses aggregators
    pipeline.add_step(ValidateArtifactsStep())
    pipeline.add_step(SaveArtifactsStep())
    
    pipeline.execute(context)
```

```python
# app/ml/training/steps/compute_stats.py

class ComputeStatsStep(TrainingStep):
    def run(self, context):
        # Strategy pattern: each aggregator is independent
        baseline = BaselineAggregator(context.config).compute(df)
        role_strength = RoleStrengthAggregator(context.config).compute(df)
        synergy = SynergyAggregator(context.config).compute(df, baseline)
        counter = CounterAggregator(context.config).compute(df, baseline)
        
        context.artifact_stats = ArtifactStats(...)
```

**Pros**: Testable, extensible, reusable, flexible  
**Cons**: More files, more abstraction

---

## Key Patterns

### 1. Strategy Pattern (Aggregators)
**Purpose**: Encapsulate different statistical computations

```python
class BaseAggregator(ABC):
    @abstractmethod
    def compute(self, df: pd.DataFrame, **kwargs) -> Any:
        pass

class RoleStrengthAggregator(BaseAggregator):
    def compute(self, df: pd.DataFrame) -> dict[str, dict[str, float]]:
        # Compute role-specific winrates
        ...

class SynergyAggregator(BaseAggregator):
    def compute(self, df: pd.DataFrame, global_winrates: dict) -> dict[str, dict[str, LiftStat]]:
        # Compute synergy lifts
        ...
```

**Benefits**:
- ✅ Each aggregator is independently testable
- ✅ Easy to add new aggregators
- ✅ Aggregators can be used outside the pipeline
- ✅ Clear separation of concerns

---

### 2. Pipeline Pattern (Orchestration)
**Purpose**: Compose steps into a configurable workflow

```python
class TrainingStep(ABC):
    name: str
    
    @abstractmethod
    def run(self, context: TrainingContext) -> None:
        pass

class TrainingPipeline:
    def __init__(self):
        self.steps: list[TrainingStep] = []
    
    def add_step(self, step: TrainingStep) -> TrainingPipeline:
        self.steps.append(step)
        return self
    
    def execute(self, context: TrainingContext) -> None:
        for step in self.steps:
            step.run(context)
```

**Benefits**:
- ✅ Each step is independently testable
- ✅ Easy to add/remove/reorder steps
- ✅ Clear logging at each step
- ✅ Can create different pipelines for different use cases

---

### 3. Context Pattern (Shared State)
**Purpose**: Pass data between steps without tight coupling

```python
@dataclass
class TrainingContext:
    run_id: str
    config: SmoothingConfig
    state: dict[str, Any] = field(default_factory=dict)
    
    # Type-safe properties
    @property
    def participants_df(self) -> pd.DataFrame | None:
        return self.state.get("participants_df")
    
    @participants_df.setter
    def participants_df(self, value: pd.DataFrame) -> None:
        self.state["participants_df"] = value
```

**Benefits**:
- ✅ Type-safe access to shared data
- ✅ Clear contract between steps
- ✅ Easy to debug (inspect context)
- ✅ Flexible (can add new state without changing signatures)

---

## Testing Comparison

### Current (Monolithic)
```python
def test_build_tables():
    """Integration test - tests everything together"""
    run_dir = build_tables(config)
    assert run_dir.exists()
    # Hard to test individual pieces
```

### Future (Modular)
```python
def test_role_strength_aggregator():
    """Unit test - tests one aggregator"""
    agg = RoleStrengthAggregator(config)
    df = create_test_df()
    result = agg.compute(df)
    assert result["MID"]["Ahri"] == pytest.approx(0.52)

def test_compute_stats_step():
    """Unit test - tests one step with mocked context"""
    context = TrainingContext(...)
    context.participants_df = create_test_df()
    
    step = ComputeStatsStep()
    step.run(context)
    
    assert context.artifact_stats is not None

def test_pipeline_integration():
    """Integration test - tests full pipeline"""
    pipeline = TrainingPipeline()
    pipeline.add_step(LoadDataStep())
    # ... add all steps
    
    context = TrainingContext(...)
    pipeline.execute(context)
    
    assert context.artifact_stats is not None
```

---

## When to Refactor?

### ✅ Good Reasons
- Need to add many new aggregators
- Testing becomes painful
- Need different pipeline compositions
- File grows beyond ~500 lines
- Have concrete evidence current structure blocks progress

### ❌ Bad Reasons
- "It would be cleaner" (subjective)
- "Best practices say so" (context matters)
- "I read about this pattern" (don't over-engineer)
- "Might need it someday" (YAGNI principle)

---

## Migration Path

1. **Phase 1**: Extract aggregators (low risk, high value)
2. **Phase 2**: Create pipeline (medium risk, medium value)
3. **Phase 3**: Switch over (low risk, high value)
4. **Phase 4**: Cleanup (low risk, low value)

Each phase is independently shippable!

---

## References

- **Improvement Plan**: `context/ml_training_pipeline_improvement_plan.md`
- **Current Status**: `context/ml_training_current_status.md`
- **Current Code**: `backend/app/ml/build_tables.py`
- **Ingest Example**: `backend/app/ingest/pipeline.py`
