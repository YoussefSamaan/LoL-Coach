from abc import ABC, abstractmethod
from typing import Any

from core.config.settings import settings

genai: Any | None = None
openai: Any | None = None


def _get_genai() -> Any:
    global genai
    if genai is None:
        try:
            from google import genai as google_genai
        except ImportError as exc:  # pragma: no cover - import error path
            raise RuntimeError(
                "google-genai is not installed. Install backend[genai] or backend[dev]."
            ) from exc
        genai = google_genai
    return genai


def _get_openai() -> Any:
    global openai
    if openai is None:
        try:
            import openai as openai_module
        except ImportError as exc:  # pragma: no cover - import error path
            raise RuntimeError(
                "openai is not installed. Install backend[genai] or backend[dev]."
            ) from exc
        openai = openai_module
    return openai


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate text response for a given prompt (synchronous).

        Args:
            prompt: Reduced prompt string.

        Returns:
            The generated text.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def agenerate(self, prompt: str) -> str:
        """
        Generate text response for a given prompt (asynchronous).

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

        self.client = _get_genai().Client(api_key=settings.genai.gemini_api_key)
        self.model = settings.genai.gemini_model

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt
            )
            # Gemini response object has a .text property
            return response.text or ""
        except Exception as e:
            # Wrap or re-raise exceptions specific to the provider
            raise RuntimeError(f"Gemini generation failed: {e}") from e

    async def agenerate(self, prompt: str) -> str:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model, contents=prompt
            )
            return response.text or ""
        except Exception as e:
            raise RuntimeError(f"Gemini async generation failed: {e}") from e


class OpenAIClient(LLMClient):
    """OpenAI implementation of LLMClient."""

    def __init__(self) -> None:
        if not settings.genai.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        openai_module = _get_openai()
        self.client = openai_module.OpenAI(api_key=settings.genai.openai_api_key)
        self.async_client = openai_module.AsyncOpenAI(
            api_key=settings.genai.openai_api_key
        )
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

    async def agenerate(self, prompt: str) -> str:
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI async generation failed: {e}") from e


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
