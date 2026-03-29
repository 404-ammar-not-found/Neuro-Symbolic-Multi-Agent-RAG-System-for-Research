"""Backwards-compatible shim for the migrated Gemini embedder."""

from src.llm.gemini import GeminiEmbedder, GeminiClient

__all__ = ["GeminiEmbedder", "GeminiClient"]