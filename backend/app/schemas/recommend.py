from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import Region, Role


class RecommendDraftRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # User context (optional if we just want raw draft logic, but keeping for broader context)
    username: str | None = None
    region: Region | None = None

    # Draft State
    role: Role
    allies: list[str] = Field(
        default_factory=list, description="List of champion names already picked by your team"
    )
    enemies: list[str] = Field(
        default_factory=list, description="List of champion names picked by the enemy team"
    )
    bans: list[str] = Field(default_factory=list, description="List of banned champion names")

    # Configuration
    top_k: int = Field(default=5, ge=1, le=50)

    @field_validator("region", mode="before")
    @classmethod
    def _normalize_region(cls, v: object) -> object:
        if isinstance(v, str):
            return v.upper()
        return v


class Recommendation(BaseModel):
    champion: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    explanation: str | None = None


class RecommendDraftResponse(BaseModel):
    role: Role
    allies: list[str]
    enemies: list[str]
    bans: list[str]
    recommendations: list[Recommendation]
