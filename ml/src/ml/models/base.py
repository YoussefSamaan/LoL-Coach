"""Base interface for all draft recommendation models.

This module defines the abstract interface that all ML models must implement,
whether they're table-based, neural networks, GBMs, or RL agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DraftPrediction:
    """Prediction result from a draft model.

    Attributes:
        champion: Champion name
        score: Predicted win probability [0, 1]
        reasons: Human-readable explanation strings
        metadata: Optional model-specific metadata (e.g., feature importances)
    """

    champion: str
    score: float
    reasons: list[str]
    metadata: dict[str, Any] | None = None


@dataclass
class TrainingMetrics:
    """Metrics from model training.

    Attributes:
        train_samples: Number of training samples
        val_samples: Number of validation samples (if applicable)
        train_loss: Training loss/error
        val_loss: Validation loss/error (if applicable)
        custom_metrics: Model-specific metrics (e.g., accuracy, AUC)
    """

    train_samples: int
    val_samples: int | None = None
    train_loss: float | None = None
    val_loss: float | None = None
    custom_metrics: dict[str, float] | None = None


class DraftModel(ABC):
    """Abstract base class for all draft recommendation models.

    All ML models (table-based, neural nets, GBMs, RL) must implement this interface.
    This ensures:
    - Consistent training/inference APIs
    - Interchangeable models in evaluation
    - Easy A/B testing between model types

    Example:
        >>> model = TableBasedModel()
        >>> model.train(train_data)
        >>> model.save(Path("artifacts/runs/my_run"))
        >>>
        >>> # Later, load and predict
        >>> model2 = TableBasedModel.load(Path("artifacts/runs/my_run"))
        >>> predictions = model2.predict(
        ...     role="MID",
        ...     allies=["Amumu"],
        ...     enemies=["Zed"],
        ...     candidates=["Ahri", "Syndra"]
        ... )
    """

    @abstractmethod
    def train(
        self,
        train_data: Any,
        val_data: Any | None = None,
        **kwargs: Any,
    ) -> TrainingMetrics:
        """Train the model on the provided data.

        Args:
            train_data: Training data (format depends on model type)
            val_data: Optional validation data for hyperparameter tuning
            **kwargs: Model-specific training parameters

        Returns:
            TrainingMetrics with training statistics

        Raises:
            ValueError: If data format is invalid
        """
        ...

    @abstractmethod
    def predict(
        self,
        *,
        role: str,
        allies: list[str],
        enemies: list[str],
        candidates: list[str],
        **kwargs: Any,
    ) -> list[DraftPrediction]:
        """Predict win probabilities for candidate champions.

        Args:
            role: Target role (e.g., "MID", "TOP")
            allies: List of allied champion names
            enemies: List of enemy champion names
            candidates: List of candidate champions to score
            **kwargs: Model-specific prediction parameters

        Returns:
            List of DraftPrediction objects, one per candidate

        Example:
            >>> predictions = model.predict(
            ...     role="MID",
            ...     allies=["Amumu", "Jax"],
            ...     enemies=["Zed", "Lee Sin"],
            ...     candidates=["Ahri", "Syndra", "Orianna"]
            ... )
            >>> predictions[0].champion
            'Ahri'
            >>> predictions[0].score
            0.547
        """
        ...

    @abstractmethod
    def save(self, path: Path) -> None:
        """Save model artifacts to disk.

        Args:
            path: Directory to save model artifacts

        Example:
            >>> model.save(Path("artifacts/runs/20260125_120000"))
        """
        ...

    @classmethod
    @abstractmethod
    def load(cls, path: Path) -> DraftModel:
        """Load model from disk.

        Args:
            path: Directory containing model artifacts

        Returns:
            Loaded model instance

        Example:
            >>> model = TableBasedModel.load(Path("artifacts/runs/20260125_120000"))
        """
        ...

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Get model metadata and configuration.

        Returns:
            Dictionary with model type, version, hyperparameters, etc.

        Example:
            >>> model.get_model_info()
            {
                'model_type': 'table_based',
                'version': '1.0',
                'num_champions': 172,
                'training_samples': 70310
            }
        """
        ...
