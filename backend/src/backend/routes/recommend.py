from fastapi import APIRouter, Depends

from ml.scoring import ScoringConfig
from backend.schemas.recommend import RecommendDraftRequest, RecommendDraftResponse
from backend.services.recommend_service import RecommendService

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
        from backend.routes.router import get_registry

        registry = get_registry()
        config = ScoringConfig()
        _service_instance = RecommendService(registry=registry, config=config)
    return _service_instance


def get_recommend_service_state() -> dict[str, str | bool | None]:
    """Return whether the recommendation model is already cached in memory."""

    if _service_instance is None or _service_instance._bundle is None:
        return {"loaded_in_memory": False, "run_id": None}

    return {
        "loaded_in_memory": True,
        "run_id": _service_instance._cached_version,
    }


@router.post("/recommend/draft", response_model=RecommendDraftResponse)
async def recommend_draft(
    payload: RecommendDraftRequest,
    service: RecommendService = Depends(get_recommend_service),
) -> RecommendDraftResponse:
    return await service.recommend_draft(payload)
