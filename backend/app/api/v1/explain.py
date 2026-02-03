from __future__ import annotations

from fastapi import APIRouter

from app.schemas.explain import ExplainDraftRequest, ExplainDraftResponse
from app.services.explain_service import get_explain_service

router = APIRouter(prefix="/explain", tags=["Explanations"])


@router.post("/draft", response_model=ExplainDraftResponse)
async def explain_draft(payload: ExplainDraftRequest) -> ExplainDraftResponse:
    """
    Generate AI explanations for recommended champions.

    This endpoint takes a list of champion recommendations and generates
    AI-powered explanations for why each champion is a good pick.

    If no API key is configured, returns heuristic explanations instead.
    """
    service = get_explain_service()
    return await service.explain_draft(payload)
