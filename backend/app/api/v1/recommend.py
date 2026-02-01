from fastapi import APIRouter, Depends

from app.ml.scoring import ScoringConfig
from app.schemas.recommend import RecommendDraftRequest, RecommendDraftResponse
from app.services.recommend_service import RecommendService

router = APIRouter()


_service_instance: RecommendService | None = None


def get_recommend_service() -> RecommendService:
    """Get or create the singleton RecommendService instance.

    The service maintains a cached model bundle and only reloads when
    the artifact version changes (detected via ModelRegistry).
    """
    global _service_instance
    if _service_instance is None:
        # Import here to avoid circular dependency
        from app.api.v1.router import get_registry

        registry = get_registry()
        config = ScoringConfig()
        _service_instance = RecommendService(registry=registry, config=config)
    return _service_instance


@router.post("/recommend/draft", response_model=RecommendDraftResponse)
async def recommend_draft(
    payload: RecommendDraftRequest,
    service: RecommendService = Depends(get_recommend_service),
) -> RecommendDraftResponse:
    return await service.recommend_draft(payload)
