from __future__ import annotations

import re
from hashlib import sha256
from typing import Any


def doc_score(doc: Any) -> float:
    meta = getattr(doc, "metadata", {}) or {}
    score = meta.get("rerank_score", meta.get("relevance_score", 0.0))
    try:
        return float(score)
    except (TypeError, ValueError):
        return 0.0


def _order_docs_for_context(docs: list[Any]) -> list[Any]:
    # Prefer high scoring chunks while lightly diversifying by source.
    ranked = sorted(docs, key=doc_score, reverse=True)
    buckets: dict[str, list[Any]] = {}
    source_order: list[str] = []

    for doc in ranked:
        meta = getattr(doc, "metadata", {}) or {}
        source = str(meta.get("source", "unknown"))
        if source not in buckets:
            buckets[source] = []
            source_order.append(source)
        buckets[source].append(doc)

    ordered: list[Any] = []
    while True:
        added = False
        for source in source_order:
            source_docs = buckets[source]
            if source_docs:
                ordered.append(source_docs.pop(0))
                added = True
        if not added:
            break
    return ordered


def format_docs(docs: list[Any]) -> str:
    ordered = _order_docs_for_context(docs)
    return "\n\n".join(doc.page_content for doc in ordered)


def debug(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[DEBUG] {message}")


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}


def _clean_tokens(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = [t for t in cleaned.split() if t and t not in _STOPWORDS]
    return tokens


def _simplify_query(query: str) -> str:
    tokens = _clean_tokens(query)
    if not tokens:
        return query
    # Keep the leading informative tokens to reduce specificity while staying on-topic.
    return " ".join(tokens[: min(len(tokens), 12)])


def _keyword_query(query: str) -> str:
    tokens = _clean_tokens(query)
    keywords = [t for t in tokens if len(t) > 3]
    if not keywords:
        return query
    return " ".join(keywords[: min(len(keywords), 10)])


def _paraphrase_query(query: str, keywords: list[str]) -> str:
    if keywords:
        head = ", ".join(keywords[: min(len(keywords), 6)])
        return f"information about {head}"
    return f"information related to {query}"


def _query_variants(original: str) -> list[str]:
    simplified = _simplify_query(original)
    keyword_str = _keyword_query(original)
    keywords = keyword_str.split()
    paraphrased = _paraphrase_query(original, keywords)

    variants = [
        original,
        simplified,
        keyword_str,
        paraphrased,
    ]

    seen: set[str] = set()
    unique: list[str] = []
    for variant in variants:
        normalized = variant.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(normalized)
    return unique


def _doc_identity(doc: Any) -> str:
    meta = getattr(doc, "metadata", {}) or {}
    source = str(meta.get("source", ""))
    chunk_id = str(meta.get("id", ""))
    chunk_index = str(meta.get("chunk_index", ""))
    content = getattr(doc, "page_content", "")[:1000]
    fingerprint = f"{source}|{chunk_id}|{chunk_index}|{content}"
    return sha256(fingerprint.encode("utf-8", errors="ignore")).hexdigest()


def _token_overlap_score(query: str, text: str) -> float:
    query_tokens = set(_clean_tokens(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(_clean_tokens(text))
    overlap = query_tokens.intersection(text_tokens)
    return len(overlap) / len(query_tokens)


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_identity: dict[str, dict[str, Any]] = {}

    for candidate in candidates:
        doc = candidate["doc"]
        identity = _doc_identity(doc)
        score = candidate.get("score")
        rank = candidate.get("rank", 1)
        variant = candidate.get("variant", "")

        entry = by_identity.get(identity)
        if entry is None:
            by_identity[identity] = {
                "doc": doc,
                "best_similarity": float(score) if score is not None else 0.0,
                "rrf": 1.0 / (60.0 + max(rank, 1)),
                "variants": {variant} if variant else set(),
            }
            continue

        if score is not None:
            entry["best_similarity"] = max(entry["best_similarity"], float(score))
        entry["rrf"] += 1.0 / (60.0 + max(rank, 1))
        if variant:
            entry["variants"].add(variant)

    deduped: list[dict[str, Any]] = []
    for entry in by_identity.values():
        doc = entry["doc"]
        meta = getattr(doc, "metadata", {}) or {}
        if entry["variants"]:
            meta = meta | {"retrieval_variants": sorted(entry["variants"])}
        meta = meta | {
            "relevance_score": entry["best_similarity"],
            "rrf_score": entry["rrf"],
        }
        doc.metadata = meta
        deduped.append(entry)
    return deduped


def _rank_candidate(entry: dict[str, Any], question: str) -> float:
    doc = entry["doc"]
    text = getattr(doc, "page_content", "")
    semantic = float(entry.get("best_similarity", 0.0))
    rrf = float(entry.get("rrf", 0.0))
    lexical = _token_overlap_score(question, text)
    # Weighted fusion: semantic relevance + rank agreement + lexical anchor.
    return (0.6 * semantic) + (0.25 * rrf) + (0.15 * lexical)


def _rerank_candidates(entries: list[dict[str, Any]], question: str, limit: int) -> list[Any]:
    scored: list[tuple[Any, float]] = []
    for entry in entries:
        doc = entry["doc"]
        score = _rank_candidate(entry, question)
        doc.metadata = (doc.metadata or {}) | {"rerank_score": score}
        scored.append((doc, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return [doc for doc, _ in scored[:limit]]


def multi_query_search(
    vectordb: Any,
    question: str,
    candidate_k: int,
    per_query_k: int | None = None,
    debug_enabled: bool = False,
) -> list[Any]:
    variants = _query_variants(question)
    debug(debug_enabled, f"Original question: {question}")
    debug(debug_enabled, f"Query variants ({len(variants)}): {variants}")
    if not variants:
        return []

    effective_per_query_k = per_query_k or max(8, candidate_k * 2)
    debug(
        debug_enabled,
        (
            f"Retrieval knobs -> candidate_k={candidate_k}, per_query_k={effective_per_query_k}, "
            f"final_top_k_applied_later"
        ),
    )
    collected: list[dict[str, Any]] = []

    for variant in variants:
        try:
            scored = vectordb.similarity_search_with_relevance_scores(variant, k=effective_per_query_k)
            preview = [round(float(score), 4) for _, score in scored[:3] if score is not None]
            debug(debug_enabled, f"Variant '{variant}' -> {len(scored)} hits (top scores: {preview})")
            for rank, (doc, score) in enumerate(scored, start=1):
                collected.append(
                    {
                        "doc": doc,
                        "score": score,
                        "rank": rank,
                        "variant": variant,
                    }
                )
        except Exception:
            docs = vectordb.similarity_search(variant, k=effective_per_query_k)
            debug(debug_enabled, f"Variant '{variant}' -> {len(docs)} hits (fallback no relevance scores)")
            for rank, doc in enumerate(docs, start=1):
                collected.append(
                    {
                        "doc": doc,
                        "score": None,
                        "rank": rank,
                        "variant": variant,
                    }
                )

    debug(debug_enabled, f"Collected candidates before dedupe: {len(collected)}")
    deduped = _dedupe_candidates(collected)
    debug(debug_enabled, f"Candidates after dedupe: {len(deduped)}")
    reranked = _rerank_candidates(deduped, question=question, limit=candidate_k)
    for idx, doc in enumerate(reranked[: min(10, len(reranked))], start=1):
        meta = getattr(doc, "metadata", {}) or {}
        score = doc_score(doc)
        debug(
            debug_enabled,
            (
                f"Reranked #{idx}: score={score:.4f}, "
                f"source={meta.get('source', 'unknown')}, chunk={meta.get('chunk_index', '?')}, "
                f"variants={meta.get('retrieval_variants', [])}"
            ),
        )
    return reranked


__all__ = ["debug", "doc_score", "format_docs", "multi_query_search"]
