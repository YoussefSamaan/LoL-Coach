import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.router import router as v1_router
from core.logging import get_logger

logger = get_logger(__name__)
DEFAULT_ARTIFACT_REFRESH_INTERVAL_SECONDS = 5.0


def get_artifact_refresh_interval_seconds() -> float:
    raw_value = os.environ.get("ARTIFACT_REFRESH_INTERVAL_SECONDS")
    if raw_value is None:
        return DEFAULT_ARTIFACT_REFRESH_INTERVAL_SECONDS

    try:
        interval = float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid ARTIFACT_REFRESH_INTERVAL_SECONDS value %r. Using default %s.",
            raw_value,
            DEFAULT_ARTIFACT_REFRESH_INTERVAL_SECONDS,
        )
        return DEFAULT_ARTIFACT_REFRESH_INTERVAL_SECONDS

    if interval <= 0:
        logger.warning(
            "ARTIFACT_REFRESH_INTERVAL_SECONDS must be positive. Using default %s.",
            DEFAULT_ARTIFACT_REFRESH_INTERVAL_SECONDS,
        )
        return DEFAULT_ARTIFACT_REFRESH_INTERVAL_SECONDS

    return interval


def preload_recommendation_artifacts() -> None:
    from backend.routes.recommend import get_recommend_service

    service = get_recommend_service()
    try:
        if service.refresh_bundle():
            logger.info("Recommendation artifacts preloaded at startup.")
        else:
            logger.info("No recommendation artifacts available to preload at startup.")
    except Exception as exc:
        logger.warning(f"Failed to preload recommendation artifacts: {exc}")


async def watch_recommendation_artifacts(
    poll_interval: float = DEFAULT_ARTIFACT_REFRESH_INTERVAL_SECONDS,
) -> None:
    from backend.routes.recommend import get_recommend_service

    service = get_recommend_service()
    while True:
        try:
            service.refresh_bundle()
        except Exception as exc:
            logger.warning(f"Failed to refresh recommendation artifacts: {exc}")
        await asyncio.sleep(poll_interval)


@asynccontextmanager
async def lifespan(_: FastAPI):
    preload_recommendation_artifacts()
    refresh_task = asyncio.create_task(
        watch_recommendation_artifacts(get_artifact_refresh_interval_seconds())
    )
    logger.info(
        "Backend startup complete. Recommendation artifacts are preloaded when available and refreshed automatically."
    )
    try:
        yield
    finally:
        refresh_task.cancel()
        with suppress(asyncio.CancelledError):
            await refresh_task


def create_app() -> FastAPI:
    app = FastAPI(
        title="LoL Coach Draft Assistant",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "lol-coach-backend"}

    @app.get("/version")
    def version() -> dict:
        """Return current model version info from the registry."""
        from ml.registry import ModelRegistry

        registry = ModelRegistry()
        version_info = registry.get_current_version()

        if version_info is None:
            # Fallback if no registry exists
            return {"version": "0.1.0", "run_id": "unknown"}

        return {
            "version": version_info.version.lstrip(
                "v"
            ),  # Remove 'v' prefix for consistency
            "run_id": version_info.run_id,
            "timestamp": version_info.timestamp,
        }

    @app.get("/ml-status")
    def ml_status() -> dict:
        """Return artifact availability and whether the current model is loaded."""
        from ml.registry import ModelRegistry
        from backend.routes.recommend import get_recommend_service_state

        try:
            registry = ModelRegistry()
            current_version = registry.get_current_version()

            if current_version:
                service_state = get_recommend_service_state()
                loaded_in_memory = (
                    bool(service_state["loaded_in_memory"])
                    and service_state["run_id"] == current_version.run_id
                )
                return {
                    "status": "ready",
                    "run_id": current_version.run_id,
                    "timestamp": current_version.timestamp,
                    "loaded_in_memory": loaded_in_memory,
                    "message": (
                        "ML artifacts are loaded in memory."
                        if loaded_in_memory
                        else "ML artifacts are available and will load on the next recommendation request."
                    ),
                }
            else:
                return {
                    "status": "missing_artifacts",
                    "run_id": None,
                    "loaded_in_memory": False,
                    "message": "Model registry is empty or missing valid artifacts.",
                }
        except Exception as e:
            return {
                "status": "error",
                "loaded_in_memory": False,
                "message": f"Failed to retrieve registry state: {e}",
            }

    app.include_router(v1_router, prefix="/v1")
    return app


def run() -> None:
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("RELOAD", "true").lower() == "true"

    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=reload)


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    run()
