from abc import ABC, abstractmethod

from google import genai

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
        if not settings.genai.api_key:
            # We might want to log a warning or handle this gracefully,
            # but for now, we assume key is present if this client is instantiated.
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=settings.genai.api_key)
        self.model = settings.genai.model

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            # Gemini response object has a .text property
            return response.text or ""
        except Exception as e:
            # Wrap or re-raise exceptions specific to the provider
            raise RuntimeError(f"Gemini generation failed: {e}") from e


def get_client(provider: str = "gemini") -> LLMClient:
    """Factory to get the appropriate LLM client."""
    if provider.lower() == "gemini":
        return GeminiClient()
    # extendable for "openai", "anthropic", etc.
    raise ValueError(f"Unknown provider: {provider}")
