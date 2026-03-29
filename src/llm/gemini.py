from __future__ import annotations

import os
from typing import Any, Sequence

from dotenv import load_dotenv
from google import genai

DEFAULT_GENERATION_MODEL = "gemini-3-flash-preview"
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"


def _require_api_key() -> str:
    """Fetch the Gemini API key or raise a clear error."""

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    return api_key


def _build_client() -> genai.Client:
    """Create a Gemini client using the API key from the environment."""

    api_key = _require_api_key()
    return genai.Client(api_key=api_key)


class GeminiClient:
    """Generic text-generation helper for Gemini models."""

    def __init__(
        self,
        model: str = DEFAULT_GENERATION_MODEL,
        client: genai.Client | None = None,
    ) -> None:
        self.model = model
        self.client = client or _build_client()

    def generate(self, prompt: str, **kwargs: Any) -> Any:
        """Run a free-form generation request with the configured model."""

        return self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            **kwargs,
        )


class GeminiEmbedder:
    """Embedding helper for Gemini models."""

    def __init__(
        self,
        model: str = DEFAULT_EMBEDDING_MODEL,
        client: genai.Client | None = None,
    ) -> None:
        self.model = model
        self.client = client or _build_client()

    def embed(self, text: str) -> list[float]:
        """Generate a single embedding vector for text."""

        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
        )
        return self._extract_embedding(response)

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""

        return [self.embed(text) for text in texts]

    @staticmethod
    def _extract_embedding(response: Any) -> list[float]:
        """Normalize embedding response shapes from the SDK."""

        # Modern SDK: response.embeddings -> list[Embedding], use .values
        if hasattr(response, "embeddings") and response.embeddings:
            first = response.embeddings[0]
            if hasattr(first, "values"):
                return list(first.values)

        # Dict fallbacks (older SDKs / raw responses)
        if isinstance(response, dict):
            if "embeddings" in response:
                embeddings = response["embeddings"]
                if embeddings and isinstance(embeddings, list):
                    first = embeddings[0]
                    if isinstance(first, dict) and "values" in first:
                        return list(first["values"])
            if "embedding" in response:
                embedding = response["embedding"]
                if isinstance(embedding, dict) and "values" in embedding:
                    return list(embedding["values"])

        raise ValueError("Unexpected embedding response format.")
