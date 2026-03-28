"""Tests for ML base model classes."""

from ml.models.base import DraftPrediction, TrainingMetrics


def test_draft_prediction():
    """Test DraftPrediction dataclass mapping."""
    # Valid
    pred = DraftPrediction(
        champion="Ahri",
        score=0.75,
        reasons=["Good synergy"],
        metadata={"version": "1.0"},
    )
    assert pred.champion == "Ahri"
    assert pred.score == 0.75
    assert pred.metadata["version"] == "1.0"


def test_training_metrics():
    """Test TrainingMetrics dataclass mapping."""
    metrics = TrainingMetrics(
        train_samples=100,
        val_samples=20,
        train_loss=0.1,
        val_loss=0.2,
        custom_metrics={"accuracy": 0.9},
    )

    assert metrics.train_samples == 100
    assert metrics.val_loss == 0.2
    assert metrics.custom_metrics["accuracy"] == 0.9
