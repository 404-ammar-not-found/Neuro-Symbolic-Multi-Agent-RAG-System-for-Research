from __future__ import annotations

from typing import Any

from .deps import get_api_key, lc_deps
from .retrieval import debug, doc_score, format_docs, multi_query_search
from .settings import PipelineSettings


def response_text(response: Any) -> str:
    """Best-effort extraction of text content from Gemini responses."""

    if hasattr(response, "text"):
        return str(response.text)
    return str(response)


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
    deps = lc_deps()
    api_key = get_api_key()

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

    def invoke(payload: dict[str, str]) -> dict[str, Any]:
        question = payload.get("query") or payload.get("question") or ""
        candidate_k = max(settings.initial_retrieval_k, settings.top_k)
        docs = multi_query_search(
            vectordb,
            question,
            candidate_k=candidate_k,
            per_query_k=settings.per_query_k,
            debug_enabled=settings.debug_retrieval,
        )
        docs = docs[: settings.top_k]
        docs = docs or []
        debug(settings.debug_retrieval, f"Final docs passed to LLM: {len(docs)}")
        for idx, doc in enumerate(docs, start=1):
            meta = getattr(doc, "metadata", {}) or {}
            score = doc_score(doc)
            debug(
                settings.debug_retrieval,
                (
                    f"Final #{idx}: score={score:.4f}, "
                    f"source={meta.get('source', 'unknown')}, chunk={meta.get('chunk_index', '?')}"
                ),
            )
        context_text = format_docs(docs)
        answer = answer_chain.invoke(
            {"context": context_text, "question": question}
        )
        debug(settings.debug_retrieval, f"Context characters sent to LLM: {len(context_text)}")
        return {"result": answer, "source_documents": docs}

    return invoke


__all__ = ["answer_question", "build_qa_chain", "response_text"]
