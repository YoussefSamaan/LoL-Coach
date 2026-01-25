from fastapi import APIRouter, Depends

from app.ml.scoring import ScoringConfig
from app.schemas.recommend import RecommendDraftRequest, RecommendDraftResponse
from app.services.model_registry import ModelRegistry
from app.services.recommend_service import RecommendService

router = APIRouter()


def get_model_registry() -> ModelRegistry:
    return ModelRegistry()


def get_recommend_service(
    registry: ModelRegistry = Depends(get_model_registry),
) -> RecommendService:
    # Use default ScoringConfig for now.
    # In the future, we can load this from a specific model config file if needed.
    config = ScoringConfig()
    return RecommendService(registry=registry, config=config)


@router.post("/recommend/draft", response_model=RecommendDraftResponse)
def recommend_draft(
    payload: RecommendDraftRequest,
    service: RecommendService = Depends(get_recommend_service),
) -> RecommendDraftResponse:
    return service.recommend_draft(payload)
