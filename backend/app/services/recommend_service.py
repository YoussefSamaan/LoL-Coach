from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.genai.explanations import agenerate_ai_explanation
from app.ml.scoring import ScoringConfig, score_candidate
from app.schemas.recommend import RecommendDraftRequest, RecommendDraftResponse, Recommendation
from app.services.model_registry import ModelRegistry


@dataclass(frozen=True)
class RecommendService:
    registry: ModelRegistry
    config: ScoringConfig

    async def recommend_draft(self, payload: RecommendDraftRequest) -> RecommendDraftResponse:
        bundle = self.registry.load_latest()

        # Infer valid champions from role_strength stats
        # bundle.stats is ArtifactStats (Pydantic model), access fields directly
        role_stats = bundle.stats.role_strength.get(payload.role.value, {})
        all_champs = set(role_stats.keys())

        candidates = []
        if all_champs:
            taken = set(payload.allies) | set(payload.enemies) | set(payload.bans)
            candidates = [c for c in all_champs if c not in taken]

        # Convert ArtifactStats to dict for score_candidate (expects Mapping)
        stats_dict = bundle.stats.model_dump()

        scored: list[tuple[str, float, list[str]]] = []
        for candidate in candidates:
            score, reasons = score_candidate(
                candidate=candidate,
                role=payload.role.value,
                allies=payload.allies,
                enemies=payload.enemies,
                stats=stats_dict,
                config=self.config,
            )
            scored.append((candidate, score, reasons))

        scored.sort(key=lambda x: x[1], reverse=True)

        top_candidates = scored[: payload.top_k]

        # Parallel explanation generation
        explanation_tasks = [
            agenerate_ai_explanation(
                champion=champion,
                allies=payload.allies,
                enemies=payload.enemies,
                reasons=reasons,
            )
            for champion, score, reasons in top_candidates
        ]

        explanations = await asyncio.gather(*explanation_tasks)

        recs = [
            Recommendation(
                champion=champion,
                score=score,
                reasons=reasons,
                explanation=explanation,
            )
            for (champion, score, reasons), explanation in zip(top_candidates, explanations)
        ]

        return RecommendDraftResponse(
            role=payload.role,
            allies=payload.allies,
            enemies=payload.enemies,
            bans=payload.bans,
            recommendations=recs,
        )
