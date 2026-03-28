from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import os
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

_THIS_FILE = Path(__file__).resolve()


def _discover_repo_root(start: Path | None = None) -> Path:
    """Find the project root after the monolith -> multi-package split."""

    current = (start or _THIS_FILE).resolve()
    if current.is_file():
        current = current.parent

    markers = ("config.yml", "docker-compose.yml", ".git")
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in markers):
            return candidate

    # Fallback to the known repo layout: core/src/core/config/settings.py -> repo root
    return _THIS_FILE.parents[4]


# Load env from repo root
BASE_DIR = _discover_repo_root()
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


class MLPipelineStagesConfig(BaseModel):
    """Configuration for ML pipeline stages."""

    build_artifacts: bool = True
    load_model: bool = True
    evaluate: bool = True
    generate_report: bool = True


class MLPipelineBuildConfig(BaseModel):
    """Configuration for artifact building."""

    force_rebuild: bool = True  # Always rebuild by default
    min_samples: int = 100


class MLPipelineEvaluationConfig(BaseModel):
    """Configuration for model evaluation."""

    enabled: bool = True
    max_samples: int | None = 5000
    train_test_split: float = 0.8
    metrics: list[str] = Field(
        default_factory=lambda: ["recall@10", "ndcg@10", "score_correlation"]
    )


class MLPipelineReportingConfig(BaseModel):
    """Configuration for pipeline reporting."""

    save_to_file: bool = True
    log_to_console: bool = True
    include_warnings: bool = True


class MLPipelineConfig(BaseModel):
    """Complete ML pipeline configuration."""

    stages: MLPipelineStagesConfig = Field(default_factory=MLPipelineStagesConfig)
    build: MLPipelineBuildConfig = Field(default_factory=MLPipelineBuildConfig)
    evaluation: MLPipelineEvaluationConfig = Field(
        default_factory=MLPipelineEvaluationConfig
    )
    reporting: MLPipelineReportingConfig = Field(
        default_factory=MLPipelineReportingConfig
    )


class GenAIConfig(BaseModel):
    provider: str = Field(default_factory=lambda: os.getenv("GENAI_PROVIDER", "gemini"))
    # Gemini settings
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = "gemini-3-flash-preview"
    # OpenAI settings
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = "gpt-4-turbo-preview"

    @property
    def api_key(self) -> str:
        if self.provider == "openai":
            return self.openai_api_key
        return self.gemini_api_key

    @property
    def model(self) -> str:
        if self.provider == "openai":
            return self.openai_model
        return self.gemini_model


class Settings(BaseModel):
    ingest: IngestConfig
    ml: MLConfig = Field(default_factory=MLConfig)
    ml_pipeline: MLPipelineConfig = Field(default_factory=MLPipelineConfig)
    genai: GenAIConfig = Field(default_factory=GenAIConfig)

    @property
    def backend_root(self) -> Path:
        return BASE_DIR

    @property
    def artifacts_path(self) -> Path:
        return self.backend_root / self.ml.artifacts_dir / self.ml.model_name

    @property
    def champion_map_path(self) -> Path:
        filename = f"{self.ingest.paths.champion_map_filename}.{self.ingest.paths.champion_map_file_type}"
        return self.backend_root / self.ingest.paths.champion_map_dir / filename

    @property
    def manifests_root(self) -> Path:
        return (
            self.backend_root
            / self.ingest.paths.root_dir
            / self.ingest.paths.manifest_dir
        )

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
    ml_pipeline_path = config_dir / "definitions" / "ml_pipeline.yaml"

    ingest_data: dict[str, Any] = {}
    if ingest_path.exists():
        try:
            ingest_data = yaml.safe_load(ingest_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"Warning: Failed to load ingest.yaml: {e}")

    ml_pipeline_data: dict[str, Any] = {}
    if ml_pipeline_path.exists():
        try:
            ml_pipeline_data = (
                yaml.safe_load(ml_pipeline_path.read_text(encoding="utf-8")) or {}
            )
        except Exception as e:
            print(f"Warning: Failed to load ml_pipeline.yaml: {e}")

    return Settings(
        ingest=IngestConfig(**ingest_data),
        ml_pipeline=MLPipelineConfig(**ml_pipeline_data)
        if ml_pipeline_data
        else MLPipelineConfig(),
        # ml and genai configs use defaults for now
    )


settings = get_settings()
