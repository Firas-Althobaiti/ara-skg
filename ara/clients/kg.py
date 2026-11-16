"""Protocol defining the async Knowledge Graph client interface."""
from typing import List, Protocol, Any, Dict
from ara.schemas.triple import Triple
from ara.schemas.entity import EntityRef


class KnowledgeGraphClient(Protocol):
    """Async protocol for a knowledge‑graph client."""

    async def upsert_triples(self, triples: List[Triple]) -> Dict[str, Any]:
        """Insert or update triples; returns a delta describing changes."""

    async def resolve_entity(self, name: str, entity_type: str) -> EntityRef:
        """Resolve a name to a canonical EntityRef."""

    async def query_cypher(self, cypher: str, params: dict | None = None) -> List[dict]:
        """Execute a Cypher query and return results."""

    async def subgraph(self, entity_ids: List[str], depth: int = 2) -> List[Triple]:
        """Return all triples reachable from the given entity IDs up to a depth."""

    async def temporal_query(self, window: str) -> List[Triple]:
        """Return triples that were added/modified within the given time window."""

    async def ensure_schema(self) -> None:
        """Make sure the underlying store schema is ready."""
