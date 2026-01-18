from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


# Load env vars immediately on import
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


class PathsConfig(BaseModel):
    root_dir: str = "data"
    champion_map: str = "data/champion_ids.json"


class IngestConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    defaults: dict = Field(default_factory=dict)
    sources: list = Field(default_factory=list)
    save_by_run: bool = False


class Settings(BaseModel):
    ingest: IngestConfig

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def champion_map_path(self) -> Path:
        return self.backend_root / self.ingest.paths.champion_map

    @property
    def data_root(self) -> Path:
        return self.backend_root / self.ingest.paths.root_dir


@lru_cache
def get_settings() -> Settings:
    # Resolve config paths relative to this file
    config_dir = Path(__file__).resolve().parent
    ingest_path = config_dir / "definitions" / "ingest.yaml"

    # Load Ingest Config
    ingest_data: dict[str, Any] = {}
    if ingest_path.exists():
        try:
            ingest_data = yaml.safe_load(ingest_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"Warning: Failed to load ingest.yaml: {e}")

    return Settings(
        ingest=IngestConfig(**ingest_data),
    )


# Singleton accessibility
settings = get_settings()
