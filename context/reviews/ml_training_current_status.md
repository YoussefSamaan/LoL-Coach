# ML Training - Current Status & Next Steps

## ✅ Decision Made

**Keep current `build_tables.py` implementation for MVP**

The current implementation is:
- ✅ Well-structured and documented
- ✅ Reasonable size (358 lines)
- ✅ Clear, linear flow
- ✅ Properly validated with Pydantic models
- ✅ Good enough for shipping

## 📋 Current Focus: Get to 100% Coverage & Ship

### Immediate Tasks
1. **Ensure 100% line coverage** for `build_tables.py`
2. **Complete ML module refactoring** per `ml_refactor_plan_final.md`
3. **Add and commit** all working code
4. **Ship MVP**

### Deferred for Post-MVP
- Pipeline pattern refactoring (see `ml_training_pipeline_improvement_plan.md`)
- Strategy pattern for aggregators
- More modular architecture

## 📚 Documentation

### Current Implementation
- **File**: `backend/app/ml/build_tables.py`
- **Purpose**: Builds ML artifacts from parsed match data
- **Status**: Functional, ready for testing

### Future Improvements
- **Plan**: `context/ml_training_pipeline_improvement_plan.md`
- **Pattern**: Strategy Pattern (aggregators) + Pipeline Pattern (orchestration)
- **Benefits**: Better testability, extensibility, reusability
- **Timeline**: After MVP ships and is validated

### Overall Refactor Plan
- **Plan**: `context/ml_refactor_plan_final.md`
- **Scope**: Full ML module refactoring
- **Status**: In progress

## 🎯 Philosophy

> "Ship the MVP first, then iterate"

We're following a pragmatic approach:
1. ✅ Get current code to 100% coverage
2. ✅ Ship and validate with users
3. ✅ Gather real-world usage data
4. ⏸️ Refactor based on actual needs (not hypothetical ones)

This prevents:
- ❌ Over-engineering
- ❌ Analysis paralysis
- ❌ Premature optimization
- ❌ Delayed shipping

## 🔄 When to Revisit

Trigger the pipeline refactor when:
- We need to add multiple new aggregators frequently
- Testing becomes painful due to tight coupling
- We need different pipeline compositions for different use cases
- The file grows beyond ~500 lines
- We have concrete evidence that the current structure is blocking progress

## 📝 Notes

- Current implementation follows the refactor plan's structure
- All Pydantic models are in place
- Validation is properly implemented
- The code is production-ready

**Next step**: Focus on test coverage and shipping! 🚀
