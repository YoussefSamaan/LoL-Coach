from __future__ import annotations

from dataclasses import dataclass

from app.ml.artifacts import ArtifactBundle
from app.ml.scoring import ScoringConfig, score_candidate
from app.schemas.recommend import RecommendDraftRequest, RecommendDraftResponse, Recommendation
from app.services.model_registry import ModelRegistry


@dataclass
class RecommendService:
    registry: ModelRegistry
    config: ScoringConfig
    _bundle: ArtifactBundle | None = None
    _cached_version: str | None = None

    def get_bundle(self) -> ArtifactBundle:
        """Get the artifact bundle, reloading only if the version has changed."""
        current_version_info = self.registry.get_current_version()

        # Determine current version identifier
        current_version = current_version_info.run_id if current_version_info else None

        # Reload if version changed or bundle not yet loaded
        if self._bundle is None or self._cached_version != current_version:
            self._bundle = self.registry.load_latest()
            self._cached_version = current_version

        return self._bundle

    async def recommend_draft(self, payload: RecommendDraftRequest) -> RecommendDraftResponse:
        bundle = self.get_bundle()

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

        # Return recommendations without explanations (use /explain endpoint for those)
        recs = [
            Recommendation(
                champion=champion,
                score=score,
                reasons=reasons,
                explanation="",  # Empty - use /v1/explain/draft for AI explanations
            )
            for champion, score, reasons in top_candidates
        ]

        return RecommendDraftResponse(
            role=payload.role,
            allies=payload.allies,
            enemies=payload.enemies,
            bans=payload.bans,
            recommendations=recs,
        )
