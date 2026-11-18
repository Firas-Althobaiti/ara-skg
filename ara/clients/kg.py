"""Protocol defining the async Knowledge Graph client interface."""

from typing import Any, Protocol

from ara.schemas.entity import EntityRef
from ara.schemas.triple import Triple

KGDelta = dict[str, Any]  # {"added": int, "updated": int, "edges": [...]}


class KGWriteError(Exception):
    """Raised when a batch KG write fails.

    Backends guarantee atomicity: on this error no partial batch is
    persisted (Neo4j: the single transaction rolled back; NetworkX: the
    in-memory graph was restored from the pre-batch snapshot).
    """


class KnowledgeGraphClient(Protocol):
    """Async protocol for a knowledge‑graph client."""

    async def upsert_triples(self, triples: list[Triple]) -> KGDelta:
        """Insert or update triples atomically; returns a delta describing changes.

        Raises :class:`KGWriteError` on failure — after which the store is
        guaranteed to be unchanged (no partial writes).
        """

    async def rollback(self, delta: KGDelta) -> None:
        """Undo a failed batch described by *delta* (compensating action).

        Neo4j is a no-op (the batch ran in one transaction, so a failure
        already rolled back at the DB level); NetworkX restores the
        pre-batch snapshot.
        """

    async def resolve_entity(self, name: str, entity_type: str) -> EntityRef:
        """Resolve a name to a canonical EntityRef."""

    async def query_cypher(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results."""

    async def subgraph(self, entity_ids: list[str], depth: int = 2) -> list[Triple]:
        """Return all triples reachable from the given entity IDs up to a depth."""

    async def temporal_query(self, window: str) -> list[Triple]:
        """Return triples that were added/modified within the given time window."""

    async def ensure_schema(self) -> None:
        """Make sure the underlying store schema is ready."""


# Backwards-compatible short alias used by ``ara.clients.__init__``.
KGClient = KnowledgeGraphClient

__all__ = ["KGClient", "KnowledgeGraphClient", "KGDelta", "KGWriteError", "get_kg_client"]


def get_kg_client(settings: Any = None) -> KnowledgeGraphClient:
    """Build a KG client for the backend selected by ``settings.ARA_KG_BACKEND``.

    - ``"networkx"`` (default): :class:`NetworkXKnowledgeGraphClient`, an
      offline JSON-persisted graph — used by the demo and the CLI.
    - ``"neo4j"``: :class:`Neo4jKnowledgeGraphClient` with a lazily connected
      driver (the driver connects on first query, so building it is cheap).
    """
    if settings is None:
        from ara.config import get_settings

        settings = get_settings()

    backend = str(getattr(settings, "ARA_KG_BACKEND", "networkx")).lower()
    if backend == "networkx":
        from ara.clients.kg_networkx import NetworkXKnowledgeGraphClient

        return NetworkXKnowledgeGraphClient(
            storage_path=str(getattr(settings, "ARA_KG_STORE", "kg_store.json"))
        )
    if backend == "neo4j":
        from ara.clients.neo4j import Neo4jKnowledgeGraphClient

        client = Neo4jKnowledgeGraphClient(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
        )
        client.connect()
        return client
    raise ValueError(f"Unknown ARA_KG_BACKEND {backend!r} (expected 'networkx' or 'neo4j')")
