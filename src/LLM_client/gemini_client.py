"""Backwards-compatible shim for the migrated Gemini client."""

from src.llm.gemini import GeminiClient, GeminiEmbedder

__all__ = ["GeminiClient", "GeminiEmbedder"]