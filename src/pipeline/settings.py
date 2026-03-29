from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PipelineSettings:
    """Configuration for the RAG pipeline."""

    pdf_directory: Path = Path("data")
    chroma_path: str = "chroma_db"
    collection_name: str = "papers"
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 4
    initial_retrieval_k: int = 20
    per_query_k: int | None = None
    debug_retrieval: bool = True
    max_pages: int | None = 200
    log_every: int = 10
    embed_dimensions: int | None = None
    embed_model: str = "models/gemini-embedding-001"
    text_llm_model: str = "gemini-3-flash-preview"


__all__ = ["PipelineSettings"]
