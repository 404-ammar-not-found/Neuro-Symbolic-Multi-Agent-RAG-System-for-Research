from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openrouter import OpenRouter

DEFAULT_OPENROUTER_MODEL = "z-ai/glm-4.5-air:free"


def _require_api_key() -> str:
    """Fetch the OpenRouter API key or raise a clear error."""

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set.")
    return api_key


class OpenRouterClient:
    """Lightweight OpenRouter chat wrapper."""

    def __init__(self, model: str = DEFAULT_OPENROUTER_MODEL) -> None:
        self.api_key = _require_api_key()
        self.model = model

    def generate(self, prompt: str, model: str | None = None, **kwargs: Any) -> Any:
        """Send a single-turn prompt as a user message."""

        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, model=model, **kwargs)

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send arbitrary chat messages to OpenRouter."""

        with OpenRouter(api_key=self.api_key) as client:
            return client.chat.send(
                model=model or self.model,
                messages=messages,
                **kwargs,
            )
