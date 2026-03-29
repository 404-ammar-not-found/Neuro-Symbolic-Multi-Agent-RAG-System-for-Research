from __future__ import annotations

"""Entry point for running the RAG pipeline interactively."""

from src.pipeline import (
    PipelineSettings,
    answer_question,
    chunk_pdfs,
    response_text,
    run_pipeline,
)


def main() -> None:
    settings = PipelineSettings()
    run_pipeline(settings)


__all__ = [
    "PipelineSettings",
    "answer_question",
    "chunk_pdfs",
    "response_text",
    "run_pipeline",
    "main",
]


if __name__ == "__main__":
    main()