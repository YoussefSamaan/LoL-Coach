from __future__ import annotations

import logging

from backend.genai.client import get_client
from backend.genai.prompts import DraftPrompts

logger = logging.getLogger(__name__)


def build_explanation(*, champion: str, reasons: list[str]) -> str:
    """Legacy heuristic explanation builder."""
    if not reasons:
        return f"{champion} is recommended based on the current draft context."
    joined = "; ".join(reasons)
    return f"{champion}: {joined}"


def generate_ai_explanation(
    champion: str,
    allies: list[str],
    enemies: list[str],
    reasons: list[str] | None = None,
) -> str:
    """
    Generate an explanation using GenAI (Gemini).

    Args:
        champion: Recommended champion name.
        allies: List of ally champion names.
        enemies: List of enemy champion names.
        reasons: Optional list of heuristic reasons to incorporate.
    """
    from core.config.settings import settings

    if not settings.genai.api_key:
        return build_explanation(champion=champion, reasons=reasons or [])

    try:
        client = get_client()
        prompt = _build_prompt(champion, allies, enemies, reasons)
        return client.generate(prompt)
    except Exception as e:
        logger.error(f"Failed to generate AI explanation: {e}")
        # Fallback to simple construction
        return build_explanation(champion=champion, reasons=reasons or [])


async def agenerate_ai_explanation(
    champion: str,
    allies: list[str],
    enemies: list[str],
    reasons: list[str] | None = None,
) -> str:
    """
    Generate an explanation using GenAI (Gemini) asynchronously.

    Args:
        champion: Recommended champion name.
        allies: List of ally champion names.
        enemies: List of enemy champion names.
        reasons: Optional list of heuristic reasons to incorporate.
    """
    from core.config.settings import settings

    if not settings.genai.api_key:
        return build_explanation(champion=champion, reasons=reasons or [])

    try:
        client = get_client()
        prompt = _build_prompt(champion, allies, enemies, reasons)
        return await client.agenerate(prompt)
    except Exception as e:
        logger.error(f"Failed to generate AI explanation asynchronously: {e}")
        return build_explanation(champion=champion, reasons=reasons or [])


def _build_prompt(
    champion: str, allies: list[str], enemies: list[str], reasons: list[str] | None
) -> str:
    prompt = DraftPrompts.simple_explanation(champion, allies, enemies)
    if reasons:
        prompt += f"\nKey factors identified by model: {', '.join(reasons)}"
    return prompt
