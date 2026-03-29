import json
from pathlib import Path
from typing import Any

import chromadb
import math


DEFAULT_DB_PATH = "chroma_db"
DEFAULT_COLLECTION = "papers"
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "web-visualizer"
    / "public"
    / "data"
    / "chroma-graph.json"
)


def load_collection(db_path: str = DEFAULT_DB_PATH, collection_name: str = DEFAULT_COLLECTION):
    client = chromadb.PersistentClient(path=db_path)
    return client.get_or_create_collection(collection_name)


def page_items(collection, page_size: int = 500):
    offset = 0
    while True:
        batch = collection.get(
            include=["metadatas", "documents", "embeddings"],
            limit=page_size,
            offset=offset,
        )
        ids = batch.get("ids", []) or []
        if not ids:
            break
        yield batch
        offset += len(ids)


def normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def build_graph(collection):
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    embeddings: dict[str, list[float]] = {}

    for batch in page_items(collection):
        ids = batch.get("ids", []) or []
        docs = batch.get("documents", []) or []
        metas = batch.get("metadatas", []) or []
        embs = batch.get("embeddings")
        if embs is None:
            embs = []

        for idx, cid in enumerate(ids):
            meta = metas[idx] if idx < len(metas) else {}
            doc = docs[idx] if idx < len(docs) else ""
            label = (doc[:120] + "…") if len(doc) > 120 else doc
            group = meta.get("source", meta.get("file_hash", "unknown"))
            color = meta.get("color")
            nodes.append(
                {
                    "id": cid,
                    "label": label,
                    "group": group,
                    **({"color": color} if color else {}),
                }
            )

            if idx < len(embs):
                vec = embs[idx]
                if vec is None:
                    continue
                if hasattr(vec, "tolist"):
                    vec = vec.tolist()
                embeddings[cid] = normalize(list(vec))

    # Simple linking strategy: connect consecutive chunks from same source
    by_source: dict[str, list[str]] = {}
    for node in nodes:
        src = node.get("group", "unknown")
        by_source.setdefault(src, []).append(node["id"])

    for cid_list in by_source.values():
        cid_list.sort()
        for a, b in zip(cid_list, cid_list[1:]):
            links.append({"source": a, "target": b, "type": "sequence"})

    # Similarity-based links to create topical clusters
    sim_links: list[dict[str, Any]] = []
    node_ids = list(embeddings.keys())
    for i, src_id in enumerate(node_ids):
        src_vec = embeddings[src_id]
        best: list[tuple[float, str]] = []
        for j in range(i + 1, len(node_ids)):
            tgt_id = node_ids[j]
            sim = cosine_similarity(src_vec, embeddings[tgt_id])
            if sim < 0.5:
                continue
            best.append((sim, tgt_id))
        # keep top 4 similar nodes for this source
        best.sort(reverse=True)
        for sim, tgt_id in best[:4]:
            sim_links.append(
                {
                    "source": src_id,
                    "target": tgt_id,
                    "type": "similarity",
                    "similarity": round(float(sim), 4),
                }
            )

    links.extend(sim_links)
    return {"nodes": nodes, "links": links}


def merge_graphs(existing: dict | None, fresh: dict) -> dict:
    """Merge graphs without losing existing nodes/links.

    De-duplicates by node id and (source, target, type) link tuple.
    """

    if not existing:
        return fresh

    merged_nodes = {n["id"]: n for n in existing.get("nodes", [])}
    for n in fresh.get("nodes", []):
        merged_nodes.setdefault(n["id"], n)

    existing_links = existing.get("links", []) or []
    # Backfill link type for older exports
    for l in existing_links:
        if "type" not in l:
            l["type"] = "sequence"
    merged_links = {
        (
            l.get("source"),
            l.get("target"),
            l.get("type", ""),
        )
        for l in existing_links
    }

    for l in fresh.get("links", []):
        key = (l.get("source"), l.get("target"), l.get("type", ""))
        if key not in merged_links:
            merged_links.add(key)
            existing_links.append(l)

    return {"nodes": list(merged_nodes.values()), "links": existing_links}


def main(db_path: str = DEFAULT_DB_PATH, collection_name: str = DEFAULT_COLLECTION):
    collection = load_collection(db_path, collection_name)
    fresh_graph = build_graph(collection)

    existing_graph = None
    if OUTPUT_PATH.exists():
        try:
            existing_graph = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing_graph = None

    merged_graph = merge_graphs(existing_graph, fresh_graph)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(merged_graph, f, ensure_ascii=False, indent=2)

    print(
        f"Merged {len(fresh_graph['nodes'])} new nodes into graph; "
        f"now {len(merged_graph['nodes'])} nodes and {len(merged_graph['links'])} links at {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
