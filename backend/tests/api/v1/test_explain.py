import pytest
from unittest.mock import AsyncMock, patch

from app.domain.enums import Role


@pytest.mark.asyncio
async def test_explain_draft_endpoint(client):
    """Test the /v1/explain/draft endpoint."""
    payload = {
        "role": "TOP",
        "recommendations": [
            {
                "champion": "Aatrox",
                "allies": ["Ahri"],
                "enemies": ["Darius"],
                "reasons": ["Strong winrate"],
            }
        ],
    }

    # Mock the explain service
    with patch("app.api.v1.explain.get_explain_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.explain_draft = AsyncMock(
            return_value={
                "role": Role.TOP,
                "explanations": [{"champion": "Aatrox", "explanation": "Test explanation"}],
            }
        )
        mock_get_service.return_value = mock_service

        response = client.post("/v1/explain/draft", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "TOP"
        assert len(data["explanations"]) == 1
        assert data["explanations"][0]["champion"] == "Aatrox"
