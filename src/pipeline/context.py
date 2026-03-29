from __future__ import annotations

from typing import Any, Sequence


def _format_match(match: dict[str, Any]) -> str:
    meta = match.get("metadata", {}) or {}
    source = meta.get("source", "unknown")
    chunk_id = meta.get("chunk_index", "?")
    document = match.get("document", "")
    return f"[{source}#chunk{chunk_id}] {document}"


def build_context(matches: Sequence[dict[str, Any]]) -> str:
    """Construct a context string from retrieved matches."""

    return "\n\n".join(_format_match(match) for match in matches)


__all__ = ["build_context"]
