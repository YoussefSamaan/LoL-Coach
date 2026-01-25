from app.schemas.recommend import RecommendDraftRequest
from app.domain.enums import Role, Region


def test_region_normalization():
    # Test string normalization (lowercase -> uppercase)
    req = RecommendDraftRequest(
        role=Role.MID,
        region="euw",  # Lowercase
    )
    assert req.region == Region.EUW

    # Test Enum direct
    req2 = RecommendDraftRequest(role=Role.MID, region=Region.NA)
    assert req2.region == Region.NA

    # Test None (covers the 'return v' line when v is not a string)
    req3 = RecommendDraftRequest(role=Role.MID, region=None)
    assert req3.region is None


def test_response_model():
    from app.schemas.recommend import RecommendDraftResponse, Recommendation

    resp = RecommendDraftResponse(
        role=Role.TOP,
        allies=["A"],
        enemies=["B"],
        bans=[],
        recommendations=[
            Recommendation(champion="C", score=0.5, reasons=["Good"], explanation="Exp")
        ],
    )
    assert resp.role == Role.TOP
    assert len(resp.recommendations) == 1
    assert resp.recommendations[0].champion == "C"


def test_region_enum_passthrough():
    """Test that Enum regions are passed through unchanged (covers line 33)."""
    # When region is already an Enum, it should pass through the validator unchanged
    req = RecommendDraftRequest(role=Role.MID, region=Region.NA)
    assert req.region == Region.NA
    assert isinstance(req.region, Region)
