import pytest
from unittest.mock import patch, AsyncMock

from core.domain.enums import Role
from backend.schemas.explain import ChampionRecommendation, ExplainDraftRequest
from backend.services.explain_service import ExplainService


@pytest.mark.asyncio
async def test_explain_draft_with_ai():
    """Test AI explanations when API key is present."""
    service = ExplainService()

    payload = ExplainDraftRequest(
        role=Role.TOP,
        recommendations=[
            ChampionRecommendation(
                champion="Aatrox",
                allies=["Ahri"],
                enemies=["Darius"],
                reasons=["Strong winrate", "Good synergy"],
            )
        ],
    )

    with patch("backend.services.explain_service.settings") as mock_settings:
        mock_settings.genai.api_key = "test-key"

        with patch(
            "backend.services.explain_service.agenerate_ai_explanation",
            new_callable=AsyncMock,
        ) as mock_ai:
            mock_ai.return_value = "AI explanation for Aatrox"

            resp = await service.explain_draft(payload)

            assert resp.role == Role.TOP
            assert len(resp.explanations) == 1
            assert resp.explanations[0].champion == "Aatrox"
            assert "AI explanation" in resp.explanations[0].explanation
            assert mock_ai.called


@pytest.mark.asyncio
async def test_explain_draft_without_ai():
    """Test heuristic explanations when no API key."""
    service = ExplainService()

    payload = ExplainDraftRequest(
        role=Role.MID,
        recommendations=[
            ChampionRecommendation(
                champion="Ahri",
                allies=[],
                enemies=[],
                reasons=["High mobility", "Strong poke"],
            )
        ],
    )

    with patch("backend.services.explain_service.settings") as mock_settings:
        mock_settings.genai.api_key = None

        resp = await service.explain_draft(payload)

        assert resp.role == Role.MID
        assert len(resp.explanations) == 1
        assert resp.explanations[0].champion == "Ahri"
        # Should have heuristic explanation
        assert "Ahri" in resp.explanations[0].explanation


def test_get_explain_service_singleton():
    """Test that get_explain_service returns the same instance."""
    from backend.services.explain_service import get_explain_service

    # Reset singleton
    import backend.services.explain_service

    backend.services.explain_service._service_instance = None

    service1 = get_explain_service()
    service2 = get_explain_service()

    assert service1 is service2
