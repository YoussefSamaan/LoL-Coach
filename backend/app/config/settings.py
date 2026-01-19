from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

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
    processed_filename: str
    processed_file_type: str
    champion_map_dir: str
    champion_map_filename: str
    champion_map_file_type: str


class IngestConfig(BaseModel):
    paths: PathsConfig
    defaults: dict = Field(default_factory=dict)
    sources: list = Field(default_factory=list)
    save_by_run: bool = False

    @property
    def should_fetch_champion_map(self) -> bool:
        return self.defaults.get("fetch_champion_map", True)


class ScoringConfig(BaseModel):
    role_strength_weight: float = 1.0
    synergy_weight: float = 0.5
    counter_weight: float = 0.5
    off_role_penalty: float = 0.0


class Settings(BaseModel):
    ingest: IngestConfig
    scoring: ScoringConfig

    @property
    def backend_root(self) -> Path:
        return BASE_DIR

    @property
    def champion_map_path(self) -> Path:
        filename = (
            f"{self.ingest.paths.champion_map_filename}.{self.ingest.paths.champion_map_file_type}"
        )
        return self.backend_root / self.ingest.paths.champion_map_dir / filename

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


@lru_cache
def get_settings() -> Settings:
    config_dir = Path(__file__).resolve().parent
    ingest_path = config_dir / "definitions" / "ingest.yaml"
    scoring_path = config_dir / "definitions" / "scoring.yaml"

    ingest_data: dict[str, Any] = {}
    if ingest_path.exists():
        try:
            ingest_data = yaml.safe_load(ingest_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"Warning: Failed to load ingest.yaml: {e}")

    scoring_data: dict[str, Any] = {}
    if scoring_path.exists():
        try:
            scoring_data = yaml.safe_load(scoring_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"Warning: Failed to load scoring.yaml: {e}")

    return Settings(
        ingest=IngestConfig(**ingest_data),
        scoring=ScoringConfig(**scoring_data),
    )


settings = get_settings()
