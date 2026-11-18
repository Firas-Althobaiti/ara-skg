"""Vector store client wrapper around ChromaDB (lazily initialised).

Chroma and its embedding model are only loaded on first use, so importing
this module (and instantiating the client) is cheap and offline-safe.
"""

from __future__ import annotations

import asyncio
from typing import Any


class VectorStoreClient:
    """Async wrapper for adding and searching vector embeddings."""

    def __init__(self, persist_directory: str = "./vector_store"):
        self.persist_directory = persist_directory
        self._client: Any = None
        self._collection: Any = None

    def _ensure_client(self) -> None:
        """Create the Chroma client + collection on first use."""
        if self._client is not None:
            return
        try:
            import chromadb
        except ImportError as e:
            raise ImportError(
                "ChromaDB client not installed. Install with `pip install chromadb`."
            ) from e
        self._client = chromadb.PersistentClient(path=self.persist_directory)
        self._collection = self._client.get_or_create_collection(
            name="paper_chunks",
            metadata={"hnsw:space": "cosine"},
        )

    async def add_chunks(
        self,
        chunks: list[dict],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """Add chunk dicts (``{"text": ..., "metadata": ...}``) to the store."""
        self._ensure_client()
        documents = [c["text"] for c in chunks]
        metas = metadatas if metadatas is not None else [c.get("metadata", {}) for c in chunks]
        chunk_ids = (
            ids
            if ids is not None
            else [f"{c.get('paper_id', 'doc')}_{i}" for i, c in enumerate(chunks)]
        )
        await asyncio.to_thread(self._collection.add, documents, metas, chunk_ids)

    async def search(self, query: str, k: int = 10) -> list[dict]:
        """Search for similar chunks and return their metadata."""
        self._ensure_client()
        result = await asyncio.to_thread(self._collection.query, query, n_results=k)
        return result["metadatas"]

    async def add_paper(self, paper: Any) -> None:
        """Add all chunks of a paper to the vector store."""
        chunk_list = [
            {
                "text": chunk.text,
                "metadata": {"paper_id": paper.id, "chunk_index": chunk.span},
                "paper_id": paper.id,
            }
            for chunk in paper.chunks
        ]
        await self.add_chunks(chunk_list)

    async def close(self):
        """Close the underlying Chroma client (no‑op if never used)."""
        self._client = None
        self._collection = None
