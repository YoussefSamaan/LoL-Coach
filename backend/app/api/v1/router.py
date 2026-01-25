from fastapi import APIRouter

from app.api.v1.recommend import router as recommend_router

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


router.include_router(recommend_router, tags=["recommend"])
