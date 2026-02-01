from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router


def create_app() -> FastAPI:
    app = FastAPI(title="LoL Coach Draft Assistant", version="0.1.0")

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
        from app.services.model_registry import ModelRegistry

        registry = ModelRegistry()
        version_info = registry.get_current_version()

        if version_info is None:
            # Fallback if no registry exists
            return {"version": "0.1.0", "run_id": "unknown"}

        return {
            "version": version_info.version.lstrip("v"),  # Remove 'v' prefix for consistency
            "run_id": version_info.run_id,
            "timestamp": version_info.timestamp,
        }

    app.include_router(v1_router, prefix="/v1")
    return app


def run() -> None:
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("RELOAD", "true").lower() == "true"

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload)


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    run()
