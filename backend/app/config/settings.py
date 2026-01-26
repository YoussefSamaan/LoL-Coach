from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import os
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load env from root
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BASE_DIR / ".env")


class PathsConfig(BaseModel):
    root_dir: str
    raw_dir: str
    processed_dir: str
    parsed_dir: str = "parsed"
    aggregates_dir: str = "aggregates"
    processed_filename: str
    processed_file_type: str = "json"
    champion_map_dir: str
    champion_map_filename: str
    champion_map_file_type: str
    manifest_dir: str = "manifests"


class StagesConfig(BaseModel):
    fetch: bool = True
    scan: bool = True
    download: bool = True
    parse: bool = True
    aggregate: bool = True


class IngestConfig(BaseModel):
    paths: PathsConfig
    defaults: dict = Field(default_factory=dict)
    stages: StagesConfig = Field(default_factory=StagesConfig)
    sources: list = Field(default_factory=list)
    save_by_run: bool = False

    @property
    def should_fetch_champion_map(self) -> bool:
        return self.defaults.get("fetch_champion_map", False)


class MLConfig(BaseModel):
    artifacts_dir: str = "artifacts"
    model_name: str = "draft_model"


class GenAIConfig(BaseModel):
    api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    model: str = "gemini-3-flash-preview"


class Settings(BaseModel):
    ingest: IngestConfig
    ml: MLConfig = Field(default_factory=MLConfig)
    genai: GenAIConfig = Field(default_factory=GenAIConfig)

    @property
    def backend_root(self) -> Path:
        return BASE_DIR

    @property
    def artifacts_path(self) -> Path:
        return self.backend_root / self.ml.artifacts_dir / self.ml.model_name

    @property
    def champion_map_path(self) -> Path:
        filename = (
            f"{self.ingest.paths.champion_map_filename}.{self.ingest.paths.champion_map_file_type}"
        )
        return self.backend_root / self.ingest.paths.champion_map_dir / filename

    @property
    def manifests_root(self) -> Path:
        return self.backend_root / self.ingest.paths.root_dir / self.ingest.paths.manifest_dir

    @property
    def processed_file_path(self) -> Path:
        filename = f"{self.ingest.paths.processed_filename}.{self.ingest.paths.processed_file_type}"
        return (
            self.backend_root
            / self.ingest.paths.root_dir
            / self.ingest.paths.processed_dir
            / filename
        )

    @property
    def data_root(self) -> Path:
        return self.backend_root / self.ingest.paths.root_dir

    @property
    def raw_root(self) -> Path:
        return self.data_root / self.ingest.paths.raw_dir

    @property
    def parsed_root(self) -> Path:
        return self.data_root / self.ingest.paths.parsed_dir

    @property
    def aggregates_root(self) -> Path:
        return self.data_root / self.ingest.paths.aggregates_dir


@lru_cache
def get_settings() -> Settings:
    config_dir = Path(__file__).resolve().parent
    ingest_path = config_dir / "definitions" / "ingest.yaml"

    ingest_data: dict[str, Any] = {}
    if ingest_path.exists():
        try:
            ingest_data = yaml.safe_load(ingest_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"Warning: Failed to load ingest.yaml: {e}")

    return Settings(
        ingest=IngestConfig(**ingest_data),
        # ml config uses defaults for now
    )


settings = get_settings()
