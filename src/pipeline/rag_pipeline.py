from __future__ import annotations

"""RAG pipeline utilities for ingestion and question answering."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from src.pdf_parsing.text_chunker import TextChunker
from src.vectorstore import ChromaVectorStore


def _get_api_key() -> str:
    """Return the Gemini API key from env."""

    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your environment or .env file.")
    return api_key


def _lc_deps():
    """Lazy-import LangChain dependencies to avoid hard import errors at module import time."""

    try:
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore

        from langchain_community.document_loaders import PyPDFLoader
        from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
        from langchain_community.vectorstores import Chroma
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
    except ImportError as exc:  # pragma: no cover - only when deps missing
        raise ImportError(
            "LangChain dependencies are required. Install langchain, langchain-community, langchain-text-splitters, langchain-core, langchain-google-genai, and pymupdf."
        ) from exc

    return {
        "RecursiveCharacterTextSplitter": RecursiveCharacterTextSplitter,
        "PyPDFLoader": PyPDFLoader,
        "GoogleGenerativeAIEmbeddings": GoogleGenerativeAIEmbeddings,
        "ChatGoogleGenerativeAI": ChatGoogleGenerativeAI,
        "Chroma": Chroma,
        "PromptTemplate": PromptTemplate,
        "StrOutputParser": StrOutputParser,
    }


@dataclass
class PipelineSettings:
    """Configuration for the RAG pipeline."""

    pdf_directory: Path = Path("data")
    chroma_path: str = "chroma_db"
    collection_name: str = "papers"
    chunk_size: int = 1200
    chunk_overlap: int = 200
    top_k: int = 4
    max_pages: int | None = 200
    log_every: int = 10
    embed_model: str = "models/gemini-embedding-001"
    text_llm_model: str = "gemini-3-flash-preview"


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


def _format_docs(docs: list[Any]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def response_text(response: Any) -> str:
    """Best-effort extraction of text content from Gemini responses."""

    if hasattr(response, "text"):
        return str(response.text)
    return str(response)


def ingest_with_langchain(settings: PipelineSettings) -> tuple[Any, int]:
    """Ingest PDFs into Chroma using LangChain components."""

    deps = _lc_deps()
    api_key = _get_api_key()

    embeddings = deps["GoogleGenerativeAIEmbeddings"](
        model=settings.embed_model,
        google_api_key=api_key,
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


def build_context(matches: Sequence[dict[str, Any]]) -> str:
    """Construct a context string from retrieved matches."""

    return "\n\n".join(
        _format_match(match)
        for match in matches
    )


def _format_match(match: dict[str, Any]) -> str:
    meta = match.get("metadata", {}) or {}
    source = meta.get("source", "unknown")
    chunk_id = meta.get("chunk_index", "?")
    document = match.get("document", "")
    return f"[{source}#chunk{chunk_id}] {document}"


def answer_question(
    question: str,
    qa_chain: Any,
) -> tuple[str, list[dict[str, Any]]]:
    """Retrieve top-k chunks and generate a grounded answer via LangChain QA chain."""

    print("Querying vector store and calling LLM for final answer...")
    result = qa_chain({"query": question})
    answer = result.get("result", "")
    source_docs = result.get("source_documents", [])
    matches: list[dict[str, Any]] = []
    for doc in source_docs:
        matches.append({"document": doc.page_content, "metadata": doc.metadata})
    return answer, matches


def build_qa_chain(vectordb: Any, settings: PipelineSettings) -> Any:
    deps = _lc_deps()
    api_key = _get_api_key()

    llm = deps["ChatGoogleGenerativeAI"](
        model=settings.text_llm_model,
        google_api_key=api_key,
        temperature=0.2,
    )

    prompt = deps["PromptTemplate"](
        input_variables=["context", "question"],
        template=(
            "You are a research assistant. Use the provided context to answer the question.\n"
            "Cite chunk IDs like [source#chunk] when relevant. If the context is insufficient, say so.\n\n"
            "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        ),
    )

    answer_chain = prompt | llm | deps["StrOutputParser"]()
    retriever = vectordb.as_retriever(search_kwargs={"k": settings.top_k})

    def invoke(payload: dict[str, str]) -> dict[str, Any]:
        question = payload.get("query") or payload.get("question") or ""
        docs = retriever.invoke(question)
        docs = docs or []
        answer = answer_chain.invoke(
            {"context": _format_docs(docs), "question": question}
        )
        return {"result": answer, "source_documents": docs}

    return invoke


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
