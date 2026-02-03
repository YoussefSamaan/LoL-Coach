from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.config.settings import settings
from app.genai.explanations import agenerate_ai_explanation, build_explanation
from app.schemas.explain import (
    ChampionExplanation,
    ExplainDraftRequest,
    ExplainDraftResponse,
)


_service_instance: ExplainService | None = None


def get_explain_service() -> ExplainService:
    """Get or create the singleton ExplainService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ExplainService()
    return _service_instance


@dataclass
class ExplainService:
    """Service for generating AI explanations for champion recommendations."""

    async def explain_draft(self, payload: ExplainDraftRequest) -> ExplainDraftResponse:
        """
        Generate explanations for a list of champion recommendations.

        Uses AI if API key is available, otherwise falls back to heuristic explanations.
        """
        if settings.genai.api_key:
            # Generate AI explanations asynchronously
            explanation_tasks = [
                agenerate_ai_explanation(
                    champion=rec.champion,
                    allies=rec.allies,
                    enemies=rec.enemies,
                    reasons=rec.reasons,
                )
                for rec in payload.recommendations
            ]
            explanation_texts = await asyncio.gather(*explanation_tasks)
        else:
            # Use heuristic explanations (no AI)
            explanation_texts = [
                build_explanation(champion=rec.champion, reasons=rec.reasons)
                for rec in payload.recommendations
            ]

        explanations = [
            ChampionExplanation(champion=rec.champion, explanation=explanation)
            for rec, explanation in zip(payload.recommendations, explanation_texts)
        ]

        return ExplainDraftResponse(role=payload.role, explanations=explanations)
