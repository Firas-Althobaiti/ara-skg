"""Vector store client wrapper around ChromaDB (or any compatible store)."""

import asyncio
from typing import List, Dict, Any
from ara.schemas.paper import Chunk

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError as e:
    raise ImportError("ChromaDB client not installed. Install with `pip install chromadb`.") from e


class VectorStoreClient:
    """Async wrapper for adding and searching vector embeddings."""

    def __init__(self, persist_directory: str = "./vector_store"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.create_collection(
            name="paper_chunks",
            metadata={"hnsw:space": "cosine"},
            embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            ),
        )

    async def add_chunks(self, chunks: List[Dict]) -> None:
        """Add a list of chunk dicts (text + metadata) to the vector store."""
        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        ids = [f"{c['paper_id']}_{i}" for i, c in enumerate(chunks)]
        await asyncio.to_thread(self.collection.add, documents, metadatas, ids)

    async def search(self, query: str, k: int = 10) -> List[Dict]:
        """Search for similar chunks and return their metadata."""
        result = await asyncio.to_thread(self.collection.query, query, n_results=k)
        return result["metadatas"]

    async def add_paper(self, paper: "ara.schemas.paper.Paper") -> None:
        """Add all chunks of a paper to the vector store."""
        chunk_list = []
        for chunk in paper.chunks:
            metadata = {"paper_id": paper.id, "chunk_index": chunk.span}
            document = {"text": chunk.text}
            chunk_list.append({"text": document["text"], "metadata": metadata})
        await self.add_chunks(chunk_list)

    async def close(self):
        """Close the underlying Chroma client (no‑op for now)."""
        pass
