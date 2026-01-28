from abc import ABC, abstractmethod

from google import genai
import openai

from app.config.settings import settings


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate text response for a given prompt.

        Args:
            prompt: Reduced prompt string.

        Returns:
            The generated text.
        """
        pass  # pragma: no cover


class GeminiClient(LLMClient):
    """Gemini implementation of LLMClient."""

    def __init__(self) -> None:
        # Explicitly check for Gemini key
        if not settings.genai.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=settings.genai.gemini_api_key)
        self.model = settings.genai.gemini_model

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            # Gemini response object has a .text property
            return response.text or ""
        except Exception as e:
            # Wrap or re-raise exceptions specific to the provider
            raise RuntimeError(f"Gemini generation failed: {e}") from e


class OpenAIClient(LLMClient):
    """OpenAI implementation of LLMClient."""

    def __init__(self) -> None:
        if not settings.genai.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        self.client = openai.OpenAI(api_key=settings.genai.openai_api_key)
        self.model = settings.genai.openai_model

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI generation failed: {e}") from e


def get_client(provider: str | None = None) -> LLMClient:
    """Factory to get the appropriate LLM client."""
    # Use settings provider if not specified
    if provider is None:
        provider = settings.genai.provider

    if provider.lower() == "gemini":
        return GeminiClient()
    elif provider.lower() == "openai":
        return OpenAIClient()

    raise ValueError(f"Unknown provider: {provider}")
