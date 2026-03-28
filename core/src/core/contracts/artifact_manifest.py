from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ArtifactManifest(BaseModel):
    """
    Contract for ML Artifact Manifest.
    This defines the minimum strict fields required for a valid artifact run.
    """

    run_id: str
    created_at: str
    status: str = Field(description="'building' | 'ready' | 'failed'")
    model_version: str
    feature_schema_version: str
    data_window: Optional[str] = None
    artifact_paths: Dict[str, str] = Field(default_factory=dict)
    code_version: Optional[str] = None
    notes: Optional[str] = None


class MLStatusResponse(BaseModel):
    """
    Status response representation for the ML Pipeline status endpoint.
    """

    status: str = Field(
        description="'ready' | 'missing_artifacts' | 'invalid_manifest' | 'loading_failed'"
    )
    message: str
    run_id: Optional[str] = None
    timestamp: Optional[str] = None
    model_version: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
