from __future__ import annotations

from pathlib import Path
from typing import Any

from src.llm import GeminiClient, GeminiEmbedder
from src.pdf_parsing.pdf_reading import PdfReader
from src.pdf_parsing.text_chunker import TextChunker
from src.vectorstore import ChromaVectorStore


def chunk_pdfs(
    pdf_dir: Path,
    chunker: TextChunker,
    max_pages: int | None = 200,
    log_every: int = 10,
):
    """Yield chunks from PDFs with streaming extraction to reduce memory."""

    reader = PdfReader(pdf_dir)
    print(f"Reading PDFs from {pdf_dir.resolve()}...")

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        print(f"- extracting text from {pdf_path.name}")
        chunk_index = 0
        for chunk_text in chunker.split_stream(
            reader.iter_text(pdf_path, max_pages=max_pages, log_every=log_every)
        ):
            yield {
                "id": f"{pdf_path.stem}-chunk-{chunk_index}",
                "text": chunk_text,
                "metadata": {
                    "source": str(pdf_path),
                    "chunk_index": chunk_index,
                },
            }
            chunk_index += 1


def response_text(response: Any) -> str:
    """Best-effort extraction of text content from Gemini responses."""

    if hasattr(response, "text"):
        return str(response.text)
    return str(response)


def answer_question(
    question: str,
    store: ChromaVectorStore,
    embedder: GeminiEmbedder,
    generator: GeminiClient,
    top_k: int,
) -> tuple[str, list[dict[str, Any]]]:
    """Retrieve top-k chunks and generate a grounded answer."""

    print("Embedding question...")
    query_embedding = embedder.embed(question)
    print(f"Querying vector store for top {top_k} chunks...")
    matches = store.query(query_embedding, top_k=top_k)

    context = "\n\n".join(
        f"[{match['metadata'].get('source', 'unknown')}#chunk{match['metadata'].get('chunk_index', '?')}] "
        f"{match['document']}"
        for match in matches
    )

    prompt = (
        "You are a research assistant. Use the provided context to answer the question.\n"
        "Cite chunk IDs like [source#chunk] when relevant. If the context is insufficient, say so.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

    print("Calling LLM for final answer...")
    response = generator.generate(prompt)
    return response_text(response), matches


def main() -> None:
    pdf_directory = Path("data")
    chroma_path = "chroma_db"
    collection_name = "papers"
    chunk_size = 1200
    chunk_overlap = 200
    top_k = 4
    max_pages = 200  # cap pages per PDF to avoid huge loads; set to None to read all
    log_every = 10

    print("Starting RAG pipeline...")

    if not pdf_directory.exists():
        print(f"PDF directory not found: {pdf_directory}")
        return

    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    embedder = GeminiEmbedder()
    generator = GeminiClient()
    store = ChromaVectorStore(path=chroma_path, collection_name=collection_name)

    print("Chunking, embedding, and persisting to ChromaDB (streaming)...")
    chunk_count = 0
    for chunk in chunk_pdfs(
        pdf_directory,
        chunker,
        max_pages=max_pages,
        log_every=log_every,
    ):
        embedding = embedder.embed(chunk["text"])
        store.upsert(
            ids=[chunk["id"]],
            documents=[chunk["text"]],
            embeddings=[embedding],
            metadatas=[chunk["metadata"]],
        )
        chunk_count += 1
        if chunk_count % 50 == 0:
            print(f"  persisted {chunk_count} chunks so far...")

    if chunk_count == 0:
        print(f"No PDF chunks produced from {pdf_directory}.")
        return

    print(f"Finished persisting {chunk_count} chunks. Ready for questions.")

    question = input("Enter your research question (empty to quit): ").strip()
    if not question:
        print("No question provided. Exiting.")
        return

    answer, matches = answer_question(
        question=question,
        store=store,
        embedder=embedder,
        generator=generator,
        top_k=top_k,
    )

    print("\n--- Retrieved Chunks ---\n")
    for match in matches:
        meta = match["metadata"]
        print(f"[{meta.get('source', 'unknown')}#chunk{meta.get('chunk_index', '?')}]\n{match['document']}\n")

    print("--- Answer ---\n")
    print(answer)


if __name__ == "__main__":
    main()