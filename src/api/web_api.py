from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.pipeline import PipelineSettings, answer_question, build_qa_chain, ingest_with_langchain
from src.pipeline.deps import get_api_key, lc_deps

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CHROMA_DIR = REPO_ROOT / "chroma_db"


class AskRequest(BaseModel):
    question: str


class PipelineRuntime:
    """Keeps vector store + QA chain warm for API requests."""

    def __init__(self) -> None:
        self.settings = PipelineSettings(
            pdf_directory=DATA_DIR,
            chroma_path=str(CHROMA_DIR),
            debug_retrieval=False,
        )
        self.vectordb: Any | None = None
        self.qa_chain: Any | None = None
        self._lock = threading.Lock()

    def _open_vectorstore(self) -> Any:
        deps = lc_deps()
        api_key = get_api_key()
        embeddings = deps["GoogleGenerativeAIEmbeddings"](
            model=self.settings.embed_model,
            google_api_key=api_key,
            dimensions=self.settings.embed_dimensions,
        )
        Chroma = deps["Chroma"]
        return Chroma(
            collection_name=self.settings.collection_name,
            embedding_function=embeddings,
            persist_directory=self.settings.chroma_path,
        )

    def _ensure_chain(self) -> None:
        if self.vectordb is None:
            self.vectordb = self._open_vectorstore()
        if self.qa_chain is None:
            self.qa_chain = build_qa_chain(self.vectordb, self.settings)

    def ingest(self) -> int:
        with self._lock:
            self.vectordb, new_chunks = ingest_with_langchain(self.settings)
            self.qa_chain = build_qa_chain(self.vectordb, self.settings)
            return int(new_chunks)

    def ask(self, question: str) -> tuple[str, list[dict[str, Any]]]:
        with self._lock:
            self._ensure_chain()
            assert self.qa_chain is not None
            return answer_question(question=question, qa_chain=self.qa_chain)


runtime = PipelineRuntime()

app = FastAPI(title="Neuro-Symbolic RAG Web API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_pdf_name(filename: str) -> str:
    base = Path(filename or "uploaded.pdf").name
    if not base.lower().endswith(".pdf"):
        base = f"{base}.pdf"
    return base


def _refresh_graph_json() -> None:
    script_path = REPO_ROOT / "scripts" / "export_chroma_graph.py"
    if not script_path.exists():
        raise RuntimeError("Graph export script not found.")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Graph export failed.")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    safe_name = _safe_pdf_name(file.filename or "uploaded.pdf")
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / safe_name
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        counter = 1
        while target.exists():
            target = DATA_DIR / f"{stem}-{counter}{suffix}"
            counter += 1

    target.write_bytes(payload)

    try:
        new_chunks = runtime.ingest()
        _refresh_graph_json()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "message": "Upload complete and ChromaDB refreshed.",
        "filename": target.name,
        "newChunks": new_chunks,
    }


@app.post("/api/ask")
def ask(payload: AskRequest) -> dict[str, Any]:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        answer, matches = runtime.ask(question)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    used_node_ids: list[str] = []
    for match in matches:
        metadata = match.get("metadata") or {}
        chunk_id = metadata.get("id")
        if chunk_id:
            used_node_ids.append(str(chunk_id))

    deduped_ids = list(dict.fromkeys(used_node_ids))
    return {
        "answer": answer,
        "matches": matches,
        "usedNodeIds": deduped_ids,
    }
