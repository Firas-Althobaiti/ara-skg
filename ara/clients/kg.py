"""Protocol defining the async Knowledge Graph client interface."""

from typing import Any, Protocol

from ara.schemas.entity import EntityRef
from ara.schemas.triple import Triple


class KnowledgeGraphClient(Protocol):
    """Async protocol for a knowledge‑graph client."""

    async def upsert_triples(self, triples: list[Triple]) -> dict[str, Any]:
        """Insert or update triples; returns a delta describing changes."""

    async def resolve_entity(self, name: str, entity_type: str) -> EntityRef:
        """Resolve a name to a canonical EntityRef."""

    async def query_cypher(self, cypher: str, params: dict | None = None) -> list[dict]:
        """Execute a Cypher query and return results."""

    async def subgraph(self, entity_ids: list[str], depth: int = 2) -> list[Triple]:
        """Return all triples reachable from the given entity IDs up to a depth."""

    async def temporal_query(self, window: str) -> list[Triple]:
        """Return triples that were added/modified within the given time window."""

    async def ensure_schema(self) -> None:
        """Make sure the underlying store schema is ready."""
