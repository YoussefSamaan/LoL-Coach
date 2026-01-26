from unittest.mock import MagicMock, patch

import pytest
from app.genai.client import GeminiClient, get_client


@patch("app.genai.client.genai")
@patch("app.genai.client.settings")
def test_gemini_client_initialization(mock_settings, mock_genai):
    """Test GeminiClient initialization."""
    mock_settings.genai.api_key = "test_key"
    mock_settings.genai.model = "test_model"

    client = GeminiClient()

    mock_genai.configure.assert_called_with(api_key="test_key")
    mock_genai.GenerativeModel.assert_called_with("test_model")
    assert client.model is not None


@patch("app.genai.client.settings")
def test_gemini_client_missing_key(mock_settings):
    """Test initialization raises error without API key."""
    mock_settings.genai.api_key = ""

    with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
        GeminiClient()


@patch("app.genai.client.genai")
@patch("app.genai.client.settings")
def test_gemini_client_generate(mock_settings, mock_genai):
    """Test generating content using GeminiClient."""
    mock_settings.genai.api_key = "test_key"

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Generated explanation"
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    client = GeminiClient()
    response = client.generate("test prompt")

    assert response == "Generated explanation"
    mock_model.generate_content.assert_called_with("test prompt")


@patch("app.genai.client.genai")
@patch("app.genai.client.settings")
def test_gemini_client_generate_error(mock_settings, mock_genai):
    """Test handling of generation errors."""
    mock_settings.genai.api_key = "test_key"

    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("API Error")
    mock_genai.GenerativeModel.return_value = mock_model

    client = GeminiClient()

    with pytest.raises(RuntimeError, match="Gemini generation failed"):
        client.generate("test prompt")


@patch("app.genai.client.GeminiClient")
def test_get_client_defaults(mock_gemini_cls):
    """Test get_client factory returns GeminiClient by default."""
    client = get_client()
    assert mock_gemini_cls.called
    assert client is mock_gemini_cls.return_value


@patch("app.genai.client.GeminiClient")
def test_get_client_specific_provider(mock_gemini_cls):
    """Test get_client factory with specific provider."""
    client = get_client("gemini")
    assert mock_gemini_cls.called
    assert client is mock_gemini_cls.return_value


def test_get_client_unknown_provider():
    """Test get_client with unknown provider raises error."""
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        get_client("unknown")
