from __future__ import annotations

from pydantic import BaseModel, Field

from core.domain.enums import Role


class ChampionRecommendation(BaseModel):
    """A single champion recommendation to explain."""

    champion: str = Field(..., description="Champion name")
    allies: list[str] = Field(default_factory=list, description="Allied champions")
    enemies: list[str] = Field(default_factory=list, description="Enemy champions")
    reasons: list[str] = Field(
        default_factory=list, description="Heuristic reasons for recommendation"
    )


class ExplainDraftRequest(BaseModel):
    """Request to generate explanations for recommended champions."""

    role: Role = Field(..., description="Target role for the draft")
    recommendations: list[ChampionRecommendation] = Field(
        ..., description="List of champions to explain", max_length=10
    )


class ChampionExplanation(BaseModel):
    """AI-generated explanation for a champion recommendation."""

    champion: str = Field(..., description="Champion name")
    explanation: str = Field(..., description="AI-generated or heuristic explanation")


class ExplainDraftResponse(BaseModel):
    """Response containing AI explanations for champions."""

    role: Role
    explanations: list[ChampionExplanation]
