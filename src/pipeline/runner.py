from __future__ import annotations

from .ingestion import ingest_with_langchain
from .qa import answer_question, build_qa_chain
from .settings import PipelineSettings


def run_pipeline(settings: PipelineSettings) -> None:
    """Run the ingestion then interactive Q&A loop."""

    print("Starting RAG pipeline...")

    if not settings.pdf_directory.exists():
        print(f"PDF directory not found: {settings.pdf_directory}")
        return

    print("Chunking, embedding, and persisting to ChromaDB (LangChain)...")
    vectordb, chunk_count = ingest_with_langchain(settings)
    try:
        existing_docs = int(vectordb._collection.count())  # type: ignore[attr-defined]
    except Exception:
        existing_docs = 0

    if chunk_count == 0 and existing_docs == 0:
        print(f"No PDF chunks available from {settings.pdf_directory} (store is empty).")
        return

    print(f"Finished persisting {chunk_count} chunks. Ready for questions.")

    qa_chain = build_qa_chain(vectordb, settings)

    question = input("Enter your research question (empty to quit): ").strip()
    if not question:
        print("No question provided. Exiting.")
        return

    answer, matches = answer_question(
        question=question,
        qa_chain=qa_chain,
    )

    print("\n--- Retrieved Chunks ---\n")

    print("--- Answer ---\n")
    print(answer)


__all__ = ["run_pipeline"]
