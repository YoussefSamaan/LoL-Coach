"""Model registry for version management and rollback.

Manages ML model versions with support for:
- Current/previous model tracking
- Version history
- Rollback capability
- Backward compatibility with latest.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.ml.artifacts import ArtifactBundle, load_artifact_bundle
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VersionInfo(BaseModel):
    """Information about a model version.
    
    Attributes:
        run_id: Unique run identifier
        version: Semantic version (e.g., "v1.0.0")
        timestamp: Unix timestamp when registered
        metrics: Optional metrics for this version
    """
    run_id: str
    version: str
    timestamp: float
    metrics: dict[str, int | float] = Field(default_factory=dict)
    
    model_config = ConfigDict(frozen=True)


class RegistryState(BaseModel):
    """Registry state tracking current and previous models.
    
    Attributes:
        current: Run ID of the current (active) model
        previous: Run ID of the previous model (for rollback)
        versions: Map of run_id -> VersionInfo for all registered versions
    """
    current: str
    previous: Optional[str] = None
    versions: dict[str, VersionInfo] = Field(default_factory=dict)


class ModelRegistry:
    """Manages model versions and provides rollback capability.
    
    The registry maintains:
    - current: The active model being served
    - previous: The last known good model (for rollback)
    - versions: Map of all registered model versions
    
    Usage:
        >>> registry = ModelRegistry()
        >>> 
        >>> # Register new model
        >>> registry.register(run_id="20260125_120000", version="v1.0.0", metrics={"rows": 5000})
        >>> 
        >>> # Load current model
        >>> bundle = registry.load_latest()
        >>> 
        >>> # Rollback to previous
        >>> registry.rollback()
    """
    
    def __init__(self, artifacts_root: Path | None = None) -> None:
        """Initialize registry.
        
        Args:
            artifacts_root: Root directory for artifacts. Defaults to settings.artifacts_path
        """
        self._artifacts_root = artifacts_root or settings.artifacts_path
        self._registry_file = self._artifacts_root / "registry.json"
        self._latest_file = self._artifacts_root / "latest.json"  # Backward compat
        self._runs_dir = self._artifacts_root / "runs"
        
        # Ensure directories exist
        self._runs_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self) -> RegistryState:
        """Load registry state from disk.
        
        Returns:
            RegistryState with current/previous/versions
        """
        # Try registry.json first
        if self._registry_file.exists():
            data = json.loads(self._registry_file.read_text(encoding="utf-8"))
            return RegistryState(**data)
        
        # Fallback to latest.json for backward compatibility
        if self._latest_file.exists():
            data = json.loads(self._latest_file.read_text(encoding="utf-8"))
            run_id = data.get("run", "")
            if run_id:
                # Create minimal state from latest.json
                return RegistryState(
                    current=run_id,
                    previous=None,
                    versions={
                        run_id: VersionInfo(
                            run_id=run_id,
                            version="v1.0.0",
                            timestamp=time.time()
                        )
                    }
                )
        
        # No registry found
        return RegistryState(current="", previous=None, versions={})
    
    def _save_state(self, state: RegistryState) -> None:
        """Save registry state to disk.
        
        Args:
            state: RegistryState to save
        """
        self._registry_file.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8"
        )
        logger.info(f"Saved registry state: current={state.current}, previous={state.previous}")
    
    def register(
        self,
        run_id: str,
        version: str,
        metrics: dict[str, int | float] | None = None
    ) -> None:
        """Register a new model version and make it current.
        
        Args:
            run_id: Unique run identifier (e.g., "20260125_120000")
            version: Semantic version (e.g., "v1.0.0")
            metrics: Optional training metrics for this version
        """
        state = self._load_state()
        
        # Store previous current as previous
        if state.current:
            state.previous = state.current
        
        # Add new version
        version_info = VersionInfo(
            run_id=run_id,
            version=version,
            timestamp=time.time(),
            metrics=metrics or {}
        )
        state.versions[run_id] = version_info
        
        # Set as current
        state.current = run_id
        
        self._save_state(state)
        logger.info(
            f"Registered model version {version} (run_id={run_id}) as current",
            extra={"run_id": run_id, "version": version}
        )
    
    def load_latest(self) -> ArtifactBundle:
        """Load the current model artifacts.
        
        Returns:
            ArtifactBundle for current model
            
        Raises:
            ValueError: If no current model is registered
        """
        state = self._load_state()
        if not state.current:
            raise ValueError("No current model registered")
        
        return self.load_version(state.current)
    
    def load_current(self) -> ArtifactBundle:
        """Alias for load_latest() for clarity."""
        return self.load_latest()
    
    def load_version(self, run_id: str) -> ArtifactBundle:
        """Load a specific model version.
        
        Args:
            run_id: Run identifier to load
            
        Returns:
            ArtifactBundle for specified version
            
        Raises:
            ValueError: If version doesn't exist
        """
        run_dir = self._runs_dir / run_id
        if not run_dir.exists():
            raise ValueError(f"Model version {run_id} not found at {run_dir}")
        
        return load_artifact_bundle(run_dir)
    
    def rollback(self) -> None:
        """Rollback to the previous model version.
        
        Raises:
            ValueError: If no previous version exists
        """
        state = self._load_state()
        if not state.previous:
            raise ValueError("No previous model to rollback to")
        
        logger.warning(
            f"Rolling back from {state.current} to {state.previous}",
            extra={"from": state.current, "to": state.previous}
        )
        
        # Swap current and previous
        old_current = state.current
        state.current = state.previous
        state.previous = old_current
        
        self._save_state(state)
    
    def list_versions(self) -> list[VersionInfo]:
        """List all registered model versions.
        
        Returns:
            List of VersionInfo, sorted by timestamp (newest first)
        """
        state = self._load_state()
        versions = list(state.versions.values())
        versions.sort(key=lambda v: v.timestamp, reverse=True)
        return versions
    
    def get_current_version(self) -> Optional[VersionInfo]:
        """Get info about the current model version.
        
        Returns:
            VersionInfo for current model, or None if no current model
        """
        state = self._load_state()
        if not state.current:
            return None
        return state.versions.get(state.current)
