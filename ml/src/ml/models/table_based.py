"""Table-based draft model using additive lift scoring.

This is the current production model that uses pre-computed synergy/counter tables.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ml.models.base import DraftModel, DraftPrediction, TrainingMetrics
from ml.scoring import ScoringConfig, score_candidate
from ml.artifacts.manifest import load_artifact_bundle
from ml.training import ArtifactStats


class TableBasedModel(DraftModel):
    """Table-based model using synergy/counter lift tables.

    This model:
    - Computes role strength, synergy, and counter statistics from match data
    - Stores them as lookup tables
    - Uses additive lift scoring in logit space for inference

    Attributes:
        stats: Artifact statistics (role_strength, synergy, counter, etc.)
        config: Scoring configuration (weights, scaling)
        metadata: Model metadata (training info, etc.)
    """

    def __init__(
        self,
        stats: ArtifactStats | None = None,
        config: ScoringConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize table-based model.

        Args:
            stats: Pre-computed artifact statistics
            config: Scoring configuration
            metadata: Model metadata
        """
        self.stats = stats
        self.config = config or ScoringConfig()
        self.metadata = metadata or {}

    def train(
        self,
        train_data: Any,
        val_data: Any | None = None,
        **kwargs: Any,
    ) -> TrainingMetrics:
        """Train by building lookup tables from match data.

        For table-based models, "training" means computing statistics.
        This is typically done by build_tables.py, not here.

        Args:
            train_data: Path to parsed match data or pre-built ArtifactStats
            val_data: Not used for table-based models
            **kwargs: Additional parameters (e.g., smoothing, min_count)

        Returns:
            TrainingMetrics with sample counts

        Raises:
            NotImplementedError: Use build_tables.py for training
        """
        raise NotImplementedError(
            "Table-based model training is handled by build_tables.py. "
            "Use TableBasedModel.load() to load pre-built artifacts."
        )

    def predict(
        self,
        *,
        role: str,
        allies: list[str],
        enemies: list[str],
        candidates: list[str],
        **kwargs: Any,
    ) -> list[DraftPrediction]:
        """Predict win probabilities using table lookup and additive scoring.

        Args:
            role: Target role (e.g., "MID")
            allies: Allied champion names
            enemies: Enemy champion names
            candidates: Candidates to score
            **kwargs: Additional parameters (unused)

        Returns:
            List of DraftPrediction objects sorted by score (descending)
        """
        if self.stats is None:
            raise ValueError("Model not loaded. Call load() first.")

        # Convert stats to dict format expected by score_candidate
        stats_dict = self.stats.model_dump()

        predictions = []
        for candidate in candidates:
            score, reasons = score_candidate(
                candidate=candidate,
                role=role,
                allies=allies,
                enemies=enemies,
                stats=stats_dict,
                config=self.config,
            )

            predictions.append(
                DraftPrediction(
                    champion=candidate,
                    score=score,
                    reasons=reasons,
                    metadata={"model_type": "table_based"},
                )
            )

        # Sort by score descending
        predictions.sort(key=lambda p: p.score, reverse=True)
        return predictions

    def save(self, path: Path) -> None:
        """Save model artifacts to disk.

        Saves:
        - stats.json: Artifact statistics
        - config.json: Scoring configuration
        - metadata.json: Model metadata

        Args:
            path: Directory to save artifacts
        """
        if self.stats is None:
            raise ValueError("No stats to save. Train or load model first.")

        path.mkdir(parents=True, exist_ok=True)

        # Save stats
        stats_file = path / "stats.json"
        stats_file.write_text(self.stats.model_dump_json(indent=2), encoding="utf-8")

        # Save config
        config_file = path / "config.json"
        config_file.write_text(self.config.model_dump_json(indent=2), encoding="utf-8")

        # Save metadata
        metadata_file = path / "metadata.json"
        metadata_file.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> TableBasedModel:
        """Load model from disk.

        Args:
            path: Directory containing model artifacts

        Returns:
            Loaded TableBasedModel instance
        """
        # Load using existing artifact bundle loader
        bundle = load_artifact_bundle(path)

        # Load config if exists, otherwise use default
        config_file = path / "config.json"
        if config_file.exists():
            config_data = json.loads(config_file.read_text(encoding="utf-8"))
            config = ScoringConfig(**config_data)
        else:
            config = ScoringConfig()

        # Load metadata if exists
        metadata_file = path / "metadata.json"
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        else:
            metadata = {}

        return cls(stats=bundle.stats, config=config, metadata=metadata)

    def get_model_info(self) -> dict[str, Any]:
        """Get model metadata.

        Returns:
            Dictionary with model type, stats, and configuration
        """
        info: dict[str, Any] = {
            "model_type": "table_based",
            "version": "1.0",
            "config": self.config.model_dump(),
        }

        if self.stats:
            info["num_champions"] = len(self.stats.global_winrates)
            info["num_roles"] = len(self.stats.role_strength)

        info.update(self.metadata)
        return info
