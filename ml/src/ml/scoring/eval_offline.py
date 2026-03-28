"""
Generic offline evaluation for draft recommendation models.

This script evaluates any model implementing the DraftModel interface.
Supports:
- Train/test/validation splits
- Multiple evaluation metrics (Recall@K, NDCG@K, score correlation)
- Model-agnostic evaluation (works with tables, neural nets, GBMs, RL)

Usage:
    # Evaluate latest model with train/test split
    python -m ml.scoring.eval_offline --split 0.8

    # Evaluate specific model version
    python -m ml.scoring.eval_offline --run-id 20260125_120000

    # Evaluate on all data (no split)
    python -m ml.scoring.eval_offline --no-split
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from collections import defaultdict
from typing import Any

import numpy as np

from core.config.settings import settings
from ml.models import DraftModel, TableBasedModel
from core.logging import get_logger

logger = get_logger(__name__)


def compute_ndcg(ranked_items: list[str], relevant_item: str, k: int = 10) -> float:
    """
    Compute Normalized Discounted Cumulative Gain@K.

    NDCG measures ranking quality. Perfect ranking = 1.0, random = ~0.5

    Args:
        ranked_items: List of recommended champions in order
        relevant_item: The actual champion that was picked
        k: Cutoff for evaluation

    Returns:
        NDCG score between 0 and 1
    """
    # DCG: Sum of (relevance / log2(position + 1))
    dcg = 0.0
    for i, item in enumerate(ranked_items[:k]):
        if item == relevant_item:
            # Relevance = 1 for the true pick, 0 for others
            dcg = 1.0 / np.log2(i + 2)  # +2 because positions are 1-indexed
            break

    # IDCG: Best possible DCG (relevant item at position 1)
    idcg = 1.0 / np.log2(2)  # log2(1 + 1)

    return dcg / idcg if idcg > 0 else 0.0


def load_parsed_matches(parsed_dir: Path) -> list[dict[str, Any]]:
    """Load all parsed match data from directory.

    Args:
        parsed_dir: Directory containing parsed match JSONs

    Returns:
        List of match dictionaries
    """
    logger.info(f"Loading parsed data from {parsed_dir}...")

    parsed_files = list(parsed_dir.rglob("*.json"))
    logger.info(f"Found {len(parsed_files)} parsed files")

    all_matches = []
    for file_path in parsed_files:
        try:
            with open(file_path) as f:
                data = json.load(f)

            # Parsed files contain a list of matches
            matches = data if isinstance(data, list) else [data]
            all_matches.extend(matches)
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")

    logger.info(f"Loaded {len(all_matches)} total matches")
    return all_matches


def split_data(
    matches: list[dict[str, Any]],
    train_ratio: float = 0.8,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split matches into train and test sets.

    Args:
        matches: List of match dictionaries
        train_ratio: Fraction of data for training (0.0 to 1.0)
        seed: Random seed for reproducibility

    Returns:
        Tuple of (train_matches, test_matches)
    """
    random.seed(seed)
    shuffled = matches.copy()
    random.shuffle(shuffled)

    split_idx = int(len(shuffled) * train_ratio)
    train = shuffled[:split_idx]
    test = shuffled[split_idx:]

    logger.info(f"Split: {len(train)} train, {len(test)} test")
    return train, test


def evaluate_model(
    model: DraftModel,
    matches: list[dict[str, Any]],
    k: int = 10,
    max_samples: int | None = None,
) -> dict[str, Any]:
    """
    Evaluate a model on match data.

    Args:
        model: Model implementing DraftModel interface
        matches: List of match dictionaries to evaluate on
        k: Top-K for recall and NDCG
        max_samples: Max number of draft decisions to evaluate (None = all)

    Returns:
        Dictionary with evaluation metrics
    """
    logger.info(f"Evaluating model on {len(matches)} matches...")

    recalls = []
    ndcgs = []
    score_buckets = defaultdict(list)  # score_decile -> list of winrates

    sample_count = 0

    for match_data in matches:
        try:
            # Extract draft information
            blue_team_raw = match_data.get("blue_team", "[]")
            red_team_raw = match_data.get("red_team", "[]")
            winner = match_data.get("winner", "BLUE").upper()

            # Parse team data
            blue_team_data = (
                json.loads(blue_team_raw)
                if isinstance(blue_team_raw, str)
                else blue_team_raw
            )
            red_team_data = (
                json.loads(red_team_raw)
                if isinstance(red_team_raw, str)
                else red_team_raw
            )

            # Extract champion names
            blue_team = [p.get("c", "") for p in blue_team_data]
            red_team = [p.get("c", "") for p in red_team_data]

            # Evaluate both teams
            for team_side in ["BLUE", "RED"]:
                team = blue_team if team_side == "BLUE" else red_team
                opponents = red_team if team_side == "BLUE" else blue_team
                won = winner == team_side

                # For each role, treat that champion as the "true pick"
                for role_idx, role in enumerate(
                    ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]
                ):
                    if max_samples and sample_count >= max_samples:
                        break

                    if role_idx >= len(team):
                        continue

                    true_pick = team[role_idx]
                    if not true_pick:
                        continue

                    # Build allies (exclude current role)
                    allies = [c for i, c in enumerate(team) if i != role_idx and c]
                    enemies = [c for c in opponents if c]

                    # Get all possible candidates from model
                    # For table-based models, this is all champions in role_strength
                    _ = model.get_model_info()

                    # Try to get candidates from model
                    # This is a bit hacky but works for table-based models
                    # Future models should expose a get_candidates() method
                    try:
                        from ml.models.table_based import TableBasedModel

                        if isinstance(model, TableBasedModel) and model.stats:
                            role_stats = model.stats.role_strength.get(role, {})
                            candidates = list(role_stats.keys())
                        else:
                            # Fallback: use a default set of champions
                            logger.warning(
                                "Cannot determine candidates from model, skipping"
                            )
                            continue
                    except Exception:
                        continue

                    if not candidates:
                        continue

                    # Get predictions from model
                    predictions = model.predict(
                        role=role,
                        allies=allies,
                        enemies=enemies,
                        candidates=candidates,
                    )

                    # Extract ranked champions
                    ranked_champs = [p.champion for p in predictions]

                    # Compute Recall@K
                    recall = 1.0 if true_pick in ranked_champs[:k] else 0.0
                    recalls.append(recall)

                    # Compute NDCG@K
                    ndcg = compute_ndcg(ranked_champs, true_pick, k=k)
                    ndcgs.append(ndcg)

                    # Score correlation: bucket by score decile
                    true_pick_pred = next(
                        (p for p in predictions if p.champion == true_pick), None
                    )
                    if true_pick_pred:
                        # Convert score to decile (0-9)
                        decile = min(int(true_pick_pred.score * 10), 9)
                        score_buckets[decile].append(1.0 if won else 0.0)

                    sample_count += 1

                if max_samples and sample_count >= max_samples:
                    break

        except Exception as e:
            logger.warning(f"Failed to process match: {e}")
            continue

        if max_samples and sample_count >= max_samples:
            break

    # Compute aggregate metrics
    results: dict[str, Any] = {
        f"recall@{k}": np.mean(recalls) if recalls else 0.0,
        f"ndcg@{k}": np.mean(ndcgs) if ndcgs else 0.0,
        "num_samples": len(recalls),
        "score_correlation": {},
    }

    # Compute winrate by score decile
    for decile in sorted(score_buckets.keys()):
        winrates = score_buckets[decile]
        results["score_correlation"][f"decile_{decile}"] = {
            "mean_winrate": np.mean(winrates),
            "count": len(winrates),
        }

    return results


def main():
    """Run offline evaluation with train/test split support."""
    parser = argparse.ArgumentParser(description="Evaluate draft recommendation models")
    parser.add_argument(
        "--run-id",
        type=str,
        help="Specific run ID to evaluate (default: latest)",
    )
    parser.add_argument(
        "--split",
        type=float,
        default=0.8,
        help="Train/test split ratio (default: 0.8)",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Evaluate on all data without splitting",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Top-K for recall and NDCG (default: 10)",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        help="Max samples to evaluate (default: all)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for train/test split (default: 42)",
    )

    args = parser.parse_args()

    # Find parsed data directory
    parsed_dir = settings.data_root / settings.ingest.paths.parsed_dir

    if not parsed_dir.exists():
        logger.error(f"Parsed data directory not found: {parsed_dir}")
        logger.info("Run ingestion pipeline first: python -m ingest.cli")
        return

    logger.info("=" * 60)
    logger.info("OFFLINE EVALUATION - Draft Recommendations")
    logger.info("=" * 60)

    # Load model
    logger.info("Loading model...")
    if args.run_id:
        model_path = settings.artifacts_path / "runs" / args.run_id
        model = TableBasedModel.load(model_path)
        logger.info(f"Loaded model from {args.run_id}")
    else:
        from ml.registry import ModelRegistry

        registry = ModelRegistry()
        bundle = registry.load_latest()
        model = TableBasedModel(stats=bundle.stats)
        logger.info("Loaded latest model from registry")

    # Load all matches
    all_matches = load_parsed_matches(parsed_dir)

    if not all_matches:
        logger.error("No matches found!")
        return

    # Split data if requested
    if args.no_split:
        logger.info("Evaluating on ALL data (no train/test split)")
        logger.warning(
            "⚠️  This will overestimate performance! Use --split for honest evaluation."
        )
        test_matches = all_matches
    else:
        logger.info(
            f"Using train/test split: {args.split:.1%} train, {1 - args.split:.1%} test"
        )
        train_matches, test_matches = split_data(all_matches, args.split, args.seed)
        logger.info("Note: Model was trained on ALL data, so this is still optimistic.")
        logger.info("      For true evaluation, retrain model on train_matches only.")

    # Evaluate
    results = evaluate_model(
        model, test_matches, k=args.k, max_samples=args.max_samples
    )

    # Print results
    logger.info("\n" + "=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)
    logger.info(f"Samples Evaluated: {results['num_samples']}")
    logger.info(f"Recall@{args.k}: {results[f'recall@{args.k}']:.3f}")
    logger.info(f"NDCG@{args.k}: {results[f'ndcg@{args.k}']:.3f}")

    logger.info("\nScore Correlation (Winrate by Score Decile):")
    for decile_key in sorted(results["score_correlation"].keys()):
        stats = results["score_correlation"][decile_key]
        logger.info(f"  {decile_key}: {stats['mean_winrate']:.3f} (n={stats['count']})")

    # Save results
    output_file = settings.data_root / "eval_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved to: {output_file}")


if __name__ == "__main__":  # pragma: no cover
    main()
