from unittest.mock import MagicMock, patch

from app.genai.explanations import build_explanation, generate_ai_explanation


def test_build_explanation_empty_reasons():
    """Test explanation building with no reasons."""
    expl = build_explanation(champion="Ahri", reasons=[])
    assert expl == "Ahri is recommended based on the current draft context."


def test_build_explanation_with_reasons():
    """Test explanation building with reasons."""
    expl = build_explanation(champion="Ahri", reasons=["Good mobility", "High damage"])
    assert expl == "Ahri: Good mobility; High damage"


@patch("app.config.settings.settings")
@patch("app.genai.explanations.get_client")
def test_generate_ai_explanation_success(mock_get_client, mock_settings):
    """Test successful AI explanation generation."""
    mock_settings.genai.api_key = "test-key"
    mock_client = MagicMock()
    mock_client.generate.return_value = "AI generated explanation"
    mock_get_client.return_value = mock_client

    result = generate_ai_explanation(
        champion="Ahri", allies=["Malphite"], enemies=["Zed"], reasons=["Reason 1"]
    )

    assert result == "AI generated explanation"
    mock_get_client.assert_called_with()
    mock_client.generate.assert_called_once()

    # Verify prompt contains key info
    prompt_used = mock_client.generate.call_args[0][0]
    assert "Ahri" in prompt_used
    assert "Malphite" in prompt_used
    assert "Zed" in prompt_used
    assert "Reason 1" in prompt_used


@patch("app.config.settings.settings")
@patch("app.genai.explanations.get_client")
def test_generate_ai_explanation_failure(mock_get_client, mock_settings):
    """Test fallback to heuristic when AI generation fails."""
    mock_settings.genai.api_key = "test-key"
    mock_client = MagicMock()
    mock_client.generate.side_effect = Exception("API Error")
    mock_get_client.return_value = mock_client

    result = generate_ai_explanation(
        champion="Ahri", allies=["Malphite"], enemies=["Zed"], reasons=["Reason 1"]
    )

    # Should fall back to basic builder
    assert result == "Ahri: Reason 1"


@patch("app.config.settings.settings")
@patch("app.genai.explanations.get_client")
def test_generate_ai_explanation_no_api_key(mock_get_client, mock_settings):
    """Test fallback when API key is missing."""
    # Simulate missing API key
    mock_settings.genai.api_key = ""

    result = generate_ai_explanation(champion="Ahri", allies=[], enemies=[], reasons=["Reason 1"])

    # Should match fallback explanation format
    assert result == "Ahri: Reason 1"

    # Should NOT attempt to get client
    mock_get_client.assert_not_called()
