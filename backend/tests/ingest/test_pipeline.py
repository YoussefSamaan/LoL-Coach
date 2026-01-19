import pytest
from app.ingest.pipeline import PipelineContext, PipelineStep, IngestPipeline


class MockStep(PipelineStep):
    def __init__(self, name="MockStep", should_fail=False):
        self.name = name
        self.should_fail = should_fail
        self.ran = False

    def run(self, context: PipelineContext) -> None:
        if self.should_fail:
            raise ValueError("Boom")
        self.ran = True
        context.state[self.name] = "done"


def test_pipeline_execution(tmp_path):
    # Setup
    context = PipelineContext(run_id="test_run", base_dir=tmp_path)
    pipeline = IngestPipeline()
    step1 = MockStep("Step1")
    step2 = MockStep("Step2")

    pipeline.add_step(step1).add_step(step2)

    # Execute
    pipeline.execute(context)

    # Verify
    assert step1.ran
    assert step2.ran
    assert context.state["Step1"] == "done"
    assert context.state["Step2"] == "done"
    assert context.base_dir.exists()

    # Verify check_state property
    assert "Step1" in context.check_state


def test_pipeline_remove_step():
    pipeline = IngestPipeline()
    s1 = MockStep("KeepMe")
    s2 = MockStep("RemoveMe")

    pipeline.add_step(s1).add_step(s2)
    pipeline.remove_step_by_name("RemoveMe")

    assert len(pipeline.steps) == 1
    assert pipeline.steps[0].name == "KeepMe"


def test_pipeline_failure(tmp_path):
    context = PipelineContext(run_id="fail_run", base_dir=tmp_path)
    pipeline = IngestPipeline()
    fail_step = MockStep("FailStep", should_fail=True)
    next_step = MockStep("NextStep")

    pipeline.add_step(fail_step).add_step(next_step)

    with pytest.raises(ValueError, match="Boom"):
        pipeline.execute(context)

    assert fail_step.ran is False  # It raises before setting true? Check logic.
    # Logic: run code: raise. So self.ran = True is never reached.
    assert not next_step.ran


def test_pipeline_step_base(tmp_path):
    step = PipelineStep()
    with pytest.raises(NotImplementedError):
        step.run(PipelineContext("test", tmp_path))
