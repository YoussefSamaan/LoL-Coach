"""
Automated ML pipeline for startup initialization.

This module runs on backend startup to:
1. Check if ML artifacts exist
2. Build/train models if needed
3. Evaluate model performance
4. Generate a status report
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

from core.config.settings import settings
from ml.features.build_features import build_tables
from ml.scoring.eval_offline import evaluate_model, load_parsed_matches, split_data
from ml.models import TableBasedModel
from ml.registry import ModelRegistry
from ml.training import SmoothingConfig
from core.logging import get_logger

logger = get_logger(__name__)


class MLPipelineStatus:
    """Status of the ML pipeline execution."""

    def __init__(self):
        self.artifacts_exist = False
        self.artifacts_built = False
        self.model_loaded = False
        self.evaluation_run = False
        self.errors = []
        self.warnings = []
        self.metrics = {}
        self.model_info = {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert status to dictionary."""
        return {
            "timestamp": self.timestamp,
            "artifacts_exist": self.artifacts_exist,
            "artifacts_built": self.artifacts_built,
            "model_loaded": self.model_loaded,
            "evaluation_run": self.evaluation_run,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
            "model_info": self.model_info,
        }

    def save_report(self, path: Path) -> None:
        """Save status report to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        logger.info(f"Pipeline report saved to {path}")


def check_artifacts_exist() -> bool:
    """Check if ML artifacts exist.

    Returns:
        True if artifacts exist and are loadable
    """
    try:
        registry = ModelRegistry()
        current_version = registry.get_current_version()
        if current_version:
            logger.info(f"Found existing artifacts: {current_version.run_id}")
            return True
        else:
            logger.info("No artifacts found in registry")
            return False
    except Exception as e:
        logger.warning(f"Error checking artifacts: {e}")
        return False


def check_data_changed() -> bool:
    """Check if parsed data has changed since last build."""
    import hashlib

    try:
        parsed_dir = settings.data_root / settings.ingest.paths.parsed_dir
        if not parsed_dir.exists():
            return False  # No data to build from anyway

        hasher = hashlib.sha256()
        files = sorted(list(parsed_dir.rglob("*.json")))
        if not files:
            return False

        for f in files:
            stat = f.stat()
            hasher.update(f"{f.name}:{stat.st_mtime}:{stat.st_size}".encode("utf-8"))

        current_hash = hasher.hexdigest()
        hash_file = settings.data_root / "latest_data_hash.txt"

        if hash_file.exists():
            last_hash = hash_file.read_text(encoding="utf-8").strip()
            if last_hash == current_hash:
                return False  # Data hasn't changed

        return True  # Data changed or no previous hash exists
    except Exception as e:
        logger.warning(f"Failed to check data hash: {e}")
        return True  # Default to building if we can't safely check


def save_data_hash() -> None:
    """Save the current data hash after a successful build."""
    import hashlib

    try:
        parsed_dir = settings.data_root / settings.ingest.paths.parsed_dir
        if not parsed_dir.exists():
            return

        hasher = hashlib.sha256()
        files = sorted(list(parsed_dir.rglob("*.json")))
        for f in files:
            stat = f.stat()
            hasher.update(f"{f.name}:{stat.st_mtime}:{stat.st_size}".encode("utf-8"))

        current_hash = hasher.hexdigest()
        hash_file = settings.data_root / "latest_data_hash.txt"
        hash_file.write_text(current_hash, encoding="utf-8")
        logger.info("Saved data state hash for idempotency.")
    except Exception as e:
        logger.warning(f"Failed to save data hash: {e}")


def build_artifacts_if_needed(force: bool = False) -> tuple[bool, str | None]:
    """Build ML artifacts if they don't exist or if forced.

    Args:
        force: Force rebuild even if artifacts exist

    Returns:
        Tuple of (success, run_id or error_message)
    """
    try:
        # Check if parsed data exists
        parsed_dir = settings.data_root / settings.ingest.paths.parsed_dir
        if not parsed_dir.exists() or not list(parsed_dir.rglob("*.json")):
            msg = f"No parsed data found at {parsed_dir}. Run ingestion first."
            logger.warning(msg)
            return False, msg

        # Build tables
        logger.info("Building ML artifacts...")
        smoothing_config = SmoothingConfig()
        min_samples = getattr(
            getattr(getattr(settings, "ml_pipeline", None), "build", None),
            "min_samples",
            None,
        )
        if isinstance(min_samples, int):
            smoothing_config = smoothing_config.model_copy(
                update={"min_samples": min_samples}
            )

        run_id = build_tables(smoothing_config)
        logger.info(f"✅ Artifacts built successfully: {run_id}")
        return True, str(run_id) if run_id else None

    except Exception as e:
        error_msg = f"Failed to build artifacts: {e}"
        logger.error(error_msg)
        return False, error_msg


def load_model() -> tuple[TableBasedModel | None, dict]:
    """Load the current model from registry.

    Returns:
        Tuple of (model, model_info)
    """
    try:
        registry = ModelRegistry()
        bundle = registry.load_latest()
        model = TableBasedModel(stats=bundle.stats)
        model_info = model.get_model_info()

        logger.info(f"✅ Model loaded: {model_info.get('num_champions', 0)} champions")
        return model, model_info

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None, {}


def run_quick_evaluation(
    model: TableBasedModel,
    max_samples: int = 5000,
) -> dict:
    """Run quick evaluation on model.

    Args:
        model: Model to evaluate
        max_samples: Max samples to evaluate (for speed)

    Returns:
        Dictionary with evaluation metrics
    """
    try:
        parsed_dir = settings.data_root / settings.ingest.paths.parsed_dir

        # Load matches
        all_matches = load_parsed_matches(parsed_dir)
        if not all_matches:
            logger.warning("No matches found for evaluation")
            return {}

        # Use 80/20 split
        train_matches, test_matches = split_data(all_matches, train_ratio=0.8)

        # Evaluate on test set
        logger.info(f"Running quick evaluation on {len(test_matches)} test matches...")
        results = evaluate_model(model, test_matches, k=10, max_samples=max_samples)

        logger.info("✅ Evaluation complete")
        return results

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {}


def print_pipeline_report(status: MLPipelineStatus) -> None:
    """Print a formatted pipeline status report.

    Args:
        status: Pipeline status to report
    """
    logger.info("\n" + "=" * 70)
    logger.info("ML PIPELINE STATUS REPORT")
    logger.info("=" * 70)

    # Status
    logger.info(f"Timestamp: {status.timestamp}")
    logger.info(f"Artifacts Exist: {'✅' if status.artifacts_exist else '❌'}")
    logger.info(f"Artifacts Built: {'✅' if status.artifacts_built else '⏭️  Skipped'}")
    logger.info(f"Model Loaded: {'✅' if status.model_loaded else '❌'}")
    logger.info(f"Evaluation Run: {'✅' if status.evaluation_run else '⏭️  Skipped'}")

    # Model info
    if status.model_info:
        logger.info("\nModel Information:")
        logger.info(f"  Type: {status.model_info.get('model_type', 'unknown')}")
        logger.info(f"  Champions: {status.model_info.get('num_champions', 0)}")
        logger.info(f"  Roles: {status.model_info.get('num_roles', 0)}")

    # Metrics
    if status.metrics:
        logger.info("\nEvaluation Metrics:")
        logger.info(f"  Samples: {status.metrics.get('num_samples', 0)}")

        # Recall and NDCG
        for key in ["recall@10", "ndcg@10"]:
            if key in status.metrics:
                logger.info(f"  {key.upper()}: {status.metrics[key]:.3f}")

        # Score correlation
        if "score_correlation" in status.metrics:
            logger.info("\n  Score Correlation (Winrate by Score Decile):")
            for decile_key in sorted(status.metrics["score_correlation"].keys()):
                stats = status.metrics["score_correlation"][decile_key]
                logger.info(
                    f"    {decile_key}: {stats['mean_winrate']:.1%} "
                    f"(n={stats['count']})"
                )

    # Warnings
    if status.warnings:
        logger.info("\n⚠️  Warnings:")
        for warning in status.warnings:
            logger.info(f"  - {warning}")

    # Errors
    if status.errors:
        logger.info("\n❌ Errors:")
        for error in status.errors:
            logger.info(f"  - {error}")

    logger.info("=" * 70 + "\n")


def run_ml_pipeline(
    force_rebuild: bool | None = None,
    skip_evaluation: bool | None = None,
    eval_max_samples: int | None = None,
) -> MLPipelineStatus:
    """Run the complete ML pipeline.

    This function:
    1. Checks if artifacts exist
    2. Builds artifacts if needed (or if forced)
    3. Loads the model
    4. Runs evaluation (unless skipped)
    5. Generates a status report

    Args:
        force_rebuild: Override config to force rebuild (None = use config)
        skip_evaluation: Override config to skip evaluation (None = use config)
        eval_max_samples: Override config for max eval samples (None = use config)

    Returns:
        MLPipelineStatus with pipeline execution details
    """
    status = MLPipelineStatus()

    # Load configuration
    config = settings.ml_pipeline

    # Apply overrides
    should_rebuild = (
        force_rebuild if force_rebuild is not None else config.build.force_rebuild
    )
    should_evaluate = (
        not skip_evaluation
        if skip_evaluation is not None
        else config.evaluation.enabled
    )
    max_samples = (
        eval_max_samples
        if eval_max_samples is not None
        else config.evaluation.max_samples
    )

    logger.info("🚀 Starting ML pipeline...")
    logger.info(f"Configuration: rebuild={should_rebuild}, evaluate={should_evaluate}")

    # Implement data-driven ML Pipeline Idempotency
    if not should_rebuild:
        if check_data_changed():
            logger.info(
                "New data detected in parsed directory. Triggering an automated rebuild."
            )
            should_rebuild = True
        else:
            logger.info("No new data detected. Skipping automated rebuild.")

    # Step 1: Check artifacts (if not forcing rebuild)
    if not should_rebuild:
        status.artifacts_exist = check_artifacts_exist()

    # Step 2: Build artifacts if needed or forced
    if should_rebuild or not status.artifacts_exist:
        if not config.stages.build_artifacts:
            logger.info("⏭️  Artifact building disabled in config")
            status.warnings.append(
                "Artifact building disabled but artifacts may be missing"
            )
        else:
            success, result = build_artifacts_if_needed(force=should_rebuild)
            status.artifacts_built = success

            if success:
                save_data_hash()
            else:
                status.errors.append(result)
                return status
    else:
        logger.info("✅ Using existing artifacts")

    # Step 3: Load model
    if not config.stages.load_model:
        logger.info("⏭️  Model loading disabled in config")
        status.warnings.append("Model loading disabled")
        return status

    model, model_info = load_model()
    status.model_loaded = model is not None
    status.model_info = model_info

    if not model:
        status.errors.append("Failed to load model")
        return status

    # Step 4: Evaluate (optional)
    if should_evaluate and config.stages.evaluate:
        metrics = run_quick_evaluation(model, max_samples=max_samples)
        status.evaluation_run = bool(metrics)
        status.metrics = metrics

        if not metrics:
            status.warnings.append("Evaluation produced no results")
    else:
        if not config.stages.evaluate:
            logger.info("⏭️  Evaluation disabled in config")
        else:
            logger.info("⏭️  Evaluation skipped")

    # Add warning about train/test split
    if status.evaluation_run and should_rebuild:
        status.warnings.append(
            "Model was just trained on all data. Evaluation uses train/test split but "
            "metrics are still optimistic. For true evaluation, retrain on train set only."
        )

    logger.info("✅ ML pipeline complete")

    return status


def run_ml_pipeline_on_startup() -> MLPipelineStatus:
    """Run ML pipeline on backend startup.

    This is the main entry point called during backend initialization.
    Configuration is loaded from app/config/definitions/ml_pipeline.yaml

    Environment variables can override config:
    - SKIP_ML_PIPELINE=true: Skip entire pipeline
    - FORCE_REBUILD=true/false: Override config.build.force_rebuild
    - SKIP_EVALUATION=true/false: Override config.evaluation.enabled

    Returns:
        MLPipelineStatus with execution details
    """
    import os

    # Check if pipeline should be skipped entirely
    if os.environ.get("SKIP_ML_PIPELINE", "false").lower() == "true":
        logger.info("⏭️  ML pipeline skipped (SKIP_ML_PIPELINE=true)")
        status = MLPipelineStatus()
        status.warnings.append(
            "Pipeline skipped via SKIP_ML_PIPELINE environment variable"
        )
        return status

    try:
        # Get overrides from environment
        force_rebuild = None
        if "FORCE_REBUILD" in os.environ:
            force_rebuild = os.environ["FORCE_REBUILD"].lower() == "true"

        skip_evaluation = None
        if "SKIP_EVALUATION" in os.environ:
            skip_evaluation = os.environ["SKIP_EVALUATION"].lower() == "true"

        # Run pipeline with config + env overrides
        status = run_ml_pipeline(
            force_rebuild=force_rebuild,
            skip_evaluation=skip_evaluation,
        )

        # Print report if configured
        if settings.ml_pipeline.reporting.log_to_console:
            print_pipeline_report(status)

        # Save report if configured
        if settings.ml_pipeline.reporting.save_to_file:
            report_path = settings.data_root / "ml_pipeline_status.json"
            status.save_report(report_path)

        return status

    except Exception as e:
        logger.error(f"ML pipeline failed: {e}")
        status = MLPipelineStatus()
        status.errors.append(str(e))
        return status


def main():
    # Allow running as standalone script
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run ML pipeline")
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild artifacts even if they exist",
    )
    parser.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="Skip evaluation step",
    )
    parser.add_argument(
        "--eval-samples",
        type=int,
        default=5000,
        help="Max samples for evaluation (default: 5000)",
    )

    args = parser.parse_args()

    status = run_ml_pipeline(
        force_rebuild=args.force_rebuild,
        skip_evaluation=args.skip_evaluation,
        eval_max_samples=args.eval_samples,
    )

    print_pipeline_report(status)

    # Save report
    report_path = settings.data_root / "ml_pipeline_status.json"
    status.save_report(report_path)

    # Exit with error code if pipeline failed
    if status.errors:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
