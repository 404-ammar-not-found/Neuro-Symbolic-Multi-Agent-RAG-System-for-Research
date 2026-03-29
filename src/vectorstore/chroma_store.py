from __future__ import annotations

from typing import Any, Sequence

import chromadb


class ChromaVectorStore:
    """Lightweight wrapper around a Chroma collection."""

    def __init__(
        self,
        path: str = "chroma_db",
        collection_name: str = "papers",
    ) -> None:
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        ids: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        documents: Sequence[str],
        metadatas: Sequence[dict[str, Any]] | None = None,
    ) -> None:
        """Insert or update embeddings/documents with matching IDs."""

        if not (len(ids) == len(embeddings) == len(documents)):
            raise ValueError("ids, embeddings, and documents must be the same length.")
        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError("metadatas length must match ids length when provided.")

        self.collection.upsert(
            ids=list(ids),
            embeddings=list(embeddings),
            documents=list(documents),
            metadatas=list(metadatas) if metadatas is not None else None,
        )

    def file_exists(self, file_hash: str) -> bool:
        """Check whether a file (by hash) is already stored."""

        existing = self.collection.get(
            where={"file_hash": file_hash},
            limit=1,
            include=["metadatas"],
        )
        ids = existing.get("ids", []) or []
        return len(ids) > 0

    def query(self, query_embedding: Sequence[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Return the top matching documents for a query embedding."""

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        matches: list[dict[str, Any]] = []
        for index in range(len(ids)):
            matches.append(
                {
                    "id": ids[index],
                    "document": documents[index],
                    "metadata": metadatas[index] if metadatas else {},
                    "distance": distances[index] if distances else None,
                }
            )
        return matches

    def count(self) -> int:
        """Return the total number of items in the collection."""

        try:
            return int(self.collection.count())
        except Exception:
            return 0
