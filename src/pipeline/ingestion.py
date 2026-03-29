from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator

from src.pdf_parsing.text_chunker import TextChunker
from src.vectorstore import ChromaVectorStore

from .deps import get_api_key, lc_deps
from .settings import PipelineSettings


def chunk_pdfs(
    pdf_dir: Path,
    chunker: TextChunker,
    store: ChromaVectorStore,
    max_pages: int | None = 200,
    log_every: int = 10,
) -> Iterator[dict[str, Any]]:
    """Yield chunks from PDFs with streaming extraction (back-compat helper)."""

    try:
        from langchain_community.document_loaders import PyPDFLoader
    except ImportError as exc:  # pragma: no cover - requires optional dep
        raise ImportError(
            "PyPDFLoader is required for chunk_pdfs. Install langchain-community and pymupdf."
        ) from exc

    print(f"Reading PDFs from {pdf_dir.resolve()}...")

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        file_hash = sha256(pdf_path.read_bytes()).hexdigest()
        if store.file_exists(file_hash):
            print(f"- skipping {pdf_path.name} (already ingested)")
            continue

        print(f"- extracting text from {pdf_path.name}")
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        if max_pages is not None:
            pages = pages[:max_pages]

        chunk_index = 0
        for page in pages:
            for chunk_text in chunker.split(page.page_content):
                yield {
                    "id": f"{pdf_path.stem}-{file_hash[:8]}-chunk-{chunk_index}",
                    "text": chunk_text,
                    "metadata": {
                        "source": str(pdf_path),
                        "chunk_index": chunk_index,
                        "file_hash": file_hash,
                    },
                }
                chunk_index += 1


def _has_file_in_store(vectordb: Any, file_hash: str) -> bool:
    """Check by file_hash in an existing Chroma collection (LangChain wrapper)."""

    try:
        result = vectordb._collection.get(where={"file_hash": file_hash}, limit=1)  # type: ignore[attr-defined]
        ids = result.get("ids", []) or []
        return len(ids) > 0
    except Exception:
        return False


def _load_pdf_docs(pdf_path: Path, max_pages: int | None, log_every: int, loader_cls: Any) -> list[Any]:
    loader = loader_cls(str(pdf_path))
    docs = loader.load()
    if max_pages is not None:
        docs = docs[:max_pages]
    total_pages = len(docs)
    if log_every > 0 and total_pages:
        print(f"  loaded {min(total_pages, max_pages or total_pages)}/{total_pages} pages from {pdf_path.name}")
    return docs


def _split_with_citations(docs: list[Any], chunk_size: int, chunk_overlap: int, splitter_cls: Any) -> list[Any]:
    splitter = splitter_cls(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks: list[Any] = []
    per_source_counter: dict[str, int] = {}
    for doc in splitter.split_documents(docs):
        source = doc.metadata.get("source", "unknown")
        file_hash = doc.metadata.get("file_hash", "unknown")
        idx = per_source_counter.get(source, 0)
        per_source_counter[source] = idx + 1
        chunk_id = f"{Path(source).stem}-{str(file_hash)[:8]}-chunk-{idx}"
        doc.metadata["chunk_index"] = idx
        doc.metadata["id"] = chunk_id
        doc.page_content = f"[{source}#chunk{idx}] {doc.page_content}"
        chunks.append(doc)
    return chunks


def ingest_with_langchain(settings: PipelineSettings) -> tuple[Any, int]:
    """Ingest PDFs into Chroma using LangChain components."""

    deps = lc_deps()
    api_key = get_api_key()

    embeddings = deps["GoogleGenerativeAIEmbeddings"](
        model=settings.embed_model,
        google_api_key=api_key,
        dimensions=settings.embed_dimensions,
    )
    Chroma = deps["Chroma"]
    PyPDFLoader = deps["PyPDFLoader"]
    splitter_cls = deps["RecursiveCharacterTextSplitter"]

    vectordb = Chroma(
        collection_name=settings.collection_name,
        embedding_function=embeddings,
        persist_directory=settings.chroma_path,
    )

    new_chunks = 0
    print(f"Reading PDFs from {settings.pdf_directory.resolve()}...")
    for pdf_path in sorted(settings.pdf_directory.glob("*.pdf")):
        file_hash = sha256(pdf_path.read_bytes()).hexdigest()
        if _has_file_in_store(vectordb, file_hash):
            print(f"- skipping {pdf_path.name} (already ingested)")
            continue

        print(f"- ingesting {pdf_path.name}")
        docs = _load_pdf_docs(pdf_path, settings.max_pages, settings.log_every, PyPDFLoader)
        for doc in docs:
            doc.metadata["source"] = str(pdf_path)
            doc.metadata["file_hash"] = file_hash

        chunks = _split_with_citations(
            docs,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            splitter_cls=splitter_cls,
        )
        ids = [c.metadata.get("id") for c in chunks]
        vectordb.add_documents(chunks, ids=ids)
        new_chunks += len(chunks)
        if new_chunks % 50 == 0:
            print(f"  persisted {new_chunks} chunks so far...")

    vectordb.persist()
    return vectordb, new_chunks


__all__ = ["chunk_pdfs", "ingest_with_langchain"]
