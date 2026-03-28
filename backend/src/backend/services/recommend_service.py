from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from ml.artifacts.manifest import ArtifactBundle
from ml.scoring import ScoringConfig, score_candidate
from backend.schemas.recommend import (
    RecommendDraftRequest,
    RecommendDraftResponse,
    Recommendation,
)
from ml.registry import ModelRegistry
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RecommendService:
    registry: ModelRegistry
    config: ScoringConfig
    _bundle: ArtifactBundle | None = None
    _cached_version: str | None = None
    _refresh_lock: Lock = field(default_factory=Lock, repr=False)

    def refresh_bundle(self) -> bool:
        """Load or refresh the cached artifact bundle if a newer version exists."""
        with self._refresh_lock:
            current_version_info = self.registry.get_current_version()
            if not current_version_info:
                return False

            current_version = current_version_info.run_id
            if self._bundle is not None and self._cached_version == current_version:
                return True

            bundle = self.registry.load_latest()
            loaded_version = bundle.manifest.run_id
            if not isinstance(loaded_version, str) or not loaded_version:
                loaded_version = current_version

            self._bundle = bundle
            self._cached_version = loaded_version

        logger.info(f"Loaded recommendation artifacts into memory: {loaded_version}")
        return True

    def get_bundle(self) -> ArtifactBundle:
        """Get the artifact bundle, reloading only if the version has changed."""
        from fastapi import HTTPException

        try:
            if not self.refresh_bundle():
                raise HTTPException(
                    status_code=503,
                    detail="ML recommendations are currently unavailable. Artifacts missing.",
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=503, detail=f"Failed to load ML artifacts: {e}"
            )

        assert self._bundle is not None
        return self._bundle

    async def recommend_draft(
        self, payload: RecommendDraftRequest
    ) -> RecommendDraftResponse:
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
