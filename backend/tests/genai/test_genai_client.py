from unittest.mock import MagicMock, patch

import pytest
from app.genai.client import GeminiClient, OpenAIClient, get_client


@patch("app.genai.client.genai")
@patch("app.genai.client.settings")
def test_gemini_client_initialization(mock_settings, mock_genai):
    """Test GeminiClient initialization."""
    mock_settings.genai.gemini_api_key = "test_key"
    mock_settings.genai.gemini_model = "test_model"

    client = GeminiClient()

    mock_genai.Client.assert_called_with(api_key="test_key")
    assert client.model == "test_model"


@patch("app.genai.client.settings")
def test_gemini_client_missing_key(mock_settings):
    """Test initialization raises error without API key."""
    mock_settings.genai.gemini_api_key = ""

    with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
        GeminiClient()


@patch("app.genai.client.genai")
@patch("app.genai.client.settings")
def test_gemini_client_generate(mock_settings, mock_genai):
    """Test generating content using GeminiClient."""
    mock_settings.genai.gemini_api_key = "test_key"
    mock_settings.genai.gemini_model = "test_model"

    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Generated explanation"
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_genai.Client.return_value = mock_client_instance

    client = GeminiClient()
    response = client.generate("test prompt")

    assert response == "Generated explanation"
    mock_client_instance.models.generate_content.assert_called_with(
        model="test_model", contents="test prompt"
    )


@patch("app.genai.client.genai")
@patch("app.genai.client.settings")
def test_gemini_client_generate_error(mock_settings, mock_genai):
    """Test handling of generation errors."""
    mock_settings.genai.gemini_api_key = "test_key"
    mock_settings.genai.gemini_model = "test_model"

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.side_effect = Exception("API Error")
    mock_genai.Client.return_value = mock_client_instance

    client = GeminiClient()

    with pytest.raises(RuntimeError, match="Gemini generation failed"):
        client.generate("test prompt")


# --- OpenAI Tests ---


@patch("app.genai.client.openai")
@patch("app.genai.client.settings")
def test_openai_client_initialization(mock_settings, mock_openai):
    """Test OpenAIClient initialization."""
    mock_settings.genai.openai_api_key = "test_key_oa"
    mock_settings.genai.openai_model = "gpt-4o-mini"

    client = OpenAIClient()

    mock_openai.OpenAI.assert_called_with(api_key="test_key_oa")
    assert client.model == "gpt-4o-mini"


@patch("app.genai.client.settings")
def test_openai_client_missing_key(mock_settings):
    """Test initialization raises error without OpenAI API key."""
    mock_settings.genai.openai_api_key = ""

    with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
        OpenAIClient()


@patch("app.genai.client.openai")
@patch("app.genai.client.settings")
def test_openai_client_generate(mock_settings, mock_openai):
    """Test generating content using OpenAIClient."""
    mock_settings.genai.openai_api_key = "test_key_oa"
    mock_settings.genai.openai_model = "gpt-4o-mini"

    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "OpenAI explanation"
    mock_response.choices = [mock_choice]

    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai.OpenAI.return_value = mock_client_instance

    client = OpenAIClient()
    response = client.generate("test prompt")

    assert response == "OpenAI explanation"
    mock_client_instance.chat.completions.create.assert_called_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test prompt"}],
    )


@patch("app.genai.client.openai")
@patch("app.genai.client.settings")
def test_openai_client_generate_error(mock_settings, mock_openai):
    """Test handling of generation errors for OpenAI."""
    mock_settings.genai.openai_api_key = "test_key_oa"
    mock_settings.genai.openai_model = "gpt-4o-mini"

    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.side_effect = Exception("OpenAI API Error")
    mock_openai.OpenAI.return_value = mock_client_instance

    client = OpenAIClient()

    with pytest.raises(RuntimeError, match="OpenAI generation failed"):
        client.generate("test prompt")


# --- Factory Tests ---


@patch("app.genai.client.settings")
@patch("app.genai.client.GeminiClient")
def test_get_client_defaults(mock_gemini_cls, mock_settings):
    """Test get_client factory returns configured provider (default gemini)."""
    mock_settings.genai.provider = "gemini"
    client = get_client()
    assert mock_gemini_cls.called
    assert client is mock_gemini_cls.return_value


@patch("app.genai.client.settings")
@patch("app.genai.client.GeminiClient")
def test_get_client_specific_provider_gemini(mock_gemini_cls, mock_settings):
    """Test get_client factory with specific provider gemini."""
    client = get_client("gemini")
    assert mock_gemini_cls.called
    assert client is mock_gemini_cls.return_value


@patch("app.genai.client.settings")
@patch("app.genai.client.OpenAIClient")
def test_get_client_specific_provider_openai(mock_openai_cls, mock_settings):
    """Test get_client factory with specific provider openai."""
    client = get_client("openai")
    assert mock_openai_cls.called
    assert client is mock_openai_cls.return_value


@patch("app.genai.client.settings")
@patch("app.genai.client.OpenAIClient")
def test_get_client_via_settings_openai(mock_openai_cls, mock_settings):
    """Test get_client factory using settings provider."""
    mock_settings.genai.provider = "openai"
    client = get_client()
    assert mock_openai_cls.called
    assert client is mock_openai_cls.return_value


@patch("app.genai.client.settings")
def test_get_client_unknown_provider(mock_settings):
    """Test get_client with unknown provider raises error."""
    mock_settings.genai.provider = "unknown_default"

    # Test passed argument
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        get_client("unknown")

    # Test settings value
    with pytest.raises(ValueError, match="Unknown provider: unknown_default"):
        get_client()
