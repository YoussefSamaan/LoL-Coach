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
        return {"version": "0.1.0"}

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
