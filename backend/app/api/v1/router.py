from fastapi import APIRouter

from app.api.v1.explain import router as explain_router
from app.api.v1.recommend import router as recommend_router
from app.services.model_registry import ModelRegistry

router = APIRouter()

# Singleton registry instance
_registry_instance: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistry()
    return _registry_instance


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/version")
def version() -> dict:
    """Return current model version info from the registry."""
    registry = get_registry()
    version_info = registry.get_current_version()

    if version_info is None:
        # Fallback if no registry exists
        return {"version": "0.1.0", "run_id": "unknown"}

    return {
        "version": version_info.version.lstrip("v"),  # Remove 'v' prefix for consistency
        "run_id": version_info.run_id,
        "timestamp": version_info.timestamp,
    }


router.include_router(recommend_router, tags=["recommend"])
router.include_router(explain_router, tags=["explain"])
