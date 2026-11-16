"""Neo4j implementation of KnowledgeGraphClient."""

from __future__ import annotations

import asyncio
from typing import List, Dict, Any
from ara.schemas.triple import Triple
from ara.schemas.entity import EntityRef
from ara.schemas.provenance import Provenance
from ara.config import get_settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from neo4j import AsyncGraphDatabase

KGDelta = Dict[str, Any]  # simple delta representation


class Neo4jKnowledgeGraphClient:
    """Async Neo4j client implementing KnowledgeGraphClient."""

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Any = None

    async def __aenter__(self):
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.driver:
            await self.driver.close()

    @classmethod
    async def create(cls, uri: str, user: str, password: str):
        instance = cls(uri, user, password)
        await instance.__aenter__()
        return instance

    async def ensure_schema(self) -> None:
        """Create uniqueness constraints if they do not exist."""
        async with self.driver.session() as session:
            await session.run(
                """
                CREATE CONSTRAINT IF NOT EXISTS uni_entity_id
                FOR (e:Entity) REQUIRE e.id IS UNIQUE
                """
            )
            await session.run(
                """
                CREATE CONSTRAINT IF NOT EXISTS uni_triple
                FOR (t:Triple)
                WITH t.subject, t.object
                REQUIRE (t.subject.id, t.object.id) IS UNIQUE
                """
            )
            await session.run(
                """
                CREATE CONSTRAINT IF NOT EXISTS uni_triple_predicate
                FOR (t:Triple)
                WITH t.predicate
                REQUIRE t.predicate IS UNIQUE
                """
            )

    async def upsert_triples(self, triples: List[Triple]) -> KGDelta:
        """MERGE each triple (subject, object, relationship) and return a delta."""
        delta = {"added": 0, "updated": 0}
        async with self.driver.session() as session:
            for triple in triples:
                # MERGE subject entity
                await session.run(
                    """
                    MERGE (s:Entity {name: $subject_name, type: $subject_type, id: $subject_id})
                    """
                , subject_name=triple.subject.name,
                  subject_type=triple.subject.type,
                  subject_id=triple.subject.id or "")
                # MERGE object entity
                await session.run(
                    """
                    MERGE (o:Entity {name: $object_name, type: $object_type, id: $object_id})
                    """
                , object_name=triple.object.name,
                  object_type=triple.object.type,
                  object_id=triple.object.id or "")
                # MERGE relationship (using a generic 'REL' type) and set properties
                await session.run(
                    """
                    MATCH (s:Entity {name: $subject_name})
                    MATCH (o:Entity {name: $object_name})
                    MERGE (s)-[r:REL]->(o)
                    SET r.predicate = $predicate,
                        r.confidence = $conf,
                        r.provenance = $prov,
                        r.timestamp = datetime()
                    """
                , subject_name=triple.subject.name,
                  object_name=triple.object.name,
                  predicate=triple.predicate,
                  conf=triple.confidence,
                  prov=triple.provenance.dict()
                )
                delta["added"] += 1
        return delta

    async def resolve_entity(self, name: str, entity_type: str) -> EntityRef:
        """Resolve a name to a canonical EntityRef (simple name‑based resolution)."""
        return EntityRef(name=name, type=entity_type, id=name)

    async def query_cypher(self, cypher: str, params: dict | None = None) -> List[dict]:
        """Execute a Cypher query and return a list of dictionaries."""
        async with self.driver.session() as session:
            result = await session.run(cypher, params or {})
            return [record._asdict() for record in result]

    async def subgraph(self, entity_ids: List[str], depth: int = 2) -> List[Triple]:
        """Return all triples reachable from the given entity IDs up to a depth."""
        # Placeholder – actual traversal would be more sophisticated.
        return []

    async def temporal_query(self, window: str) -> List[Triple]:
        """Return triples that were added/modified within the given time window."""
        # Placeholder – real implementation would filter by timestamps.
        return []

    async def ensure_schema(self) -> None:
        """Ensure schema constraints exist (already done in ensure_schema)."""
        pass
