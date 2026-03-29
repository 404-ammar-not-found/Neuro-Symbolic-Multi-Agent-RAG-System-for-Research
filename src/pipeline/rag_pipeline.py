from __future__ import annotations

"""Compatibility facade for pipeline utilities.

Core implementation has been decomposed into focused modules:
- settings.py
- deps.py
- ingestion.py
- retrieval.py
- qa.py
- runner.py
"""

from .context import build_context
from .ingestion import chunk_pdfs, ingest_with_langchain
from .qa import answer_question, build_qa_chain, response_text
from .runner import run_pipeline
from .settings import PipelineSettings

__all__ = [
    "PipelineSettings",
    "chunk_pdfs",
    "response_text",
    "build_context",
    "answer_question",
    "ingest_with_langchain",
    "build_qa_chain",
    "run_pipeline",
]
