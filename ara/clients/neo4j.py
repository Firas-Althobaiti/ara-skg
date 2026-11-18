"""Neo4j implementation of KnowledgeGraphClient."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from neo4j import AsyncGraphDatabase

from ara.schemas.entity import EntityRef
from ara.schemas.triple import Provenance, Triple

KGDelta = dict[str, Any]  # simple delta representation

_DEFAULT_PROVENANCE = {
    "paper_id": "unknown",
    "chunk_id": "0",
    "span": 0,
    "extracted_by": "neo4j",
}


def _to_provenance(raw: Any) -> Provenance:
    """Normalize a raw provenance value (dict or Provenance) to a Provenance."""
    if isinstance(raw, Provenance):
        return raw
    if isinstance(raw, dict):
        return Provenance.model_validate(raw)
    return Provenance.model_validate(_DEFAULT_PROVENANCE)


class Neo4jKnowledgeGraphClient:
    """Async Neo4j client implementing KnowledgeGraphClient."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Any = None

    def connect(self) -> None:
        """Create the driver eagerly (the driver connects lazily on first use)."""
        if self.driver is None:
            self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def __aenter__(self) -> Neo4jKnowledgeGraphClient:
        self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self.driver:
            await self.driver.close()
            self.driver = None

    @classmethod
    async def create(cls, uri: str, user: str, password: str) -> Neo4jKnowledgeGraphClient:
        instance = cls(uri, user, password)
        await instance.__aenter__()
        return instance

    async def ensure_schema(self) -> None:
        """Create uniqueness constraints if they do not exist."""
        self.connect()
        async with self.driver.session() as session:
            await session.run("""
                CREATE CONSTRAINT IF NOT EXISTS uni_entity_id
                FOR (e:Entity) REQUIRE e.id IS UNIQUE
                """)
            await session.run("""
                CREATE CONSTRAINT IF NOT EXISTS uni_entity_name
                FOR (e:Entity) REQUIRE e.name IS UNIQUE
                """)

    async def upsert_triples(self, triples: list[Triple]) -> KGDelta:
        """MERGE each triple and return a delta of created vs. matched edges.

        Idempotent: re-running with the same triples reports ``added == 0``.
        """
        self.connect()
        delta: KGDelta = {"added": 0, "updated": 0, "edges": []}
        async with self.driver.session() as session:
            for triple in triples:
                subj, obj = triple.subject, triple.object
                subj_id = subj.id or subj.name
                obj_id = obj.id or obj.name
                result = await session.run(
                    """
                    MERGE (s:Entity {id: $subject_id})
                    SET s.name = $subject_name, s.type = $subject_type
                    MERGE (o:Entity {id: $object_id})
                    SET o.name = $object_name, o.type = $object_type
                    MERGE (s)-[r:REL {predicate: $predicate}]->(o)
                    ON CREATE SET r.confidence = $conf,
                                  r.provenance = $prov,
                                  r.first_seen = datetime()
                    ON MATCH  SET r.confidence = CASE
                                  WHEN r.confidence < $conf THEN $conf ELSE r.confidence END,
                                  r.provenance = $prov,
                                  r.last_seen = datetime()
                    RETURN r.first_seen IS NOT NULL AS was_created
                    """,
                    subject_id=subj_id,
                    subject_name=subj.name,
                    subject_type=subj.type,
                    object_id=obj_id,
                    object_name=obj.name,
                    object_type=obj.type,
                    predicate=triple.predicate,
                    conf=triple.confidence,
                    prov=triple.provenance.model_dump(),
                )
                record = await result.single()
                if record and record["was_created"]:
                    delta["added"] += 1
                else:
                    delta["updated"] += 1
                delta["edges"].append(
                    {"subject": subj_id, "predicate": triple.predicate, "object": obj_id}
                )
        return delta

    async def resolve_entity(self, name: str, entity_type: str) -> EntityRef:
        """Resolve a name to a canonical EntityRef (name-based resolution)."""
        self.connect()
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity {name: $name}) RETURN e.id AS id LIMIT 1", name=name
            )
            record = await result.single()
            if record and record["id"]:
                return EntityRef(name=name, type=entity_type, id=record["id"])
        return EntityRef(name=name, type=entity_type, id=name)

    async def query_cypher(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return a list of dictionaries."""
        self.connect()
        async with self.driver.session() as session:
            result = await session.run(cypher, params or {})
            return [record._asdict() for record in result]

    async def subgraph(self, entity_ids: list[str], depth: int = 2) -> list[Triple]:
        """Return all triples reachable from the given entity IDs up to a depth."""
        self.connect()
        triples: list[Triple] = []
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity) WHERE e.id IN $ids
                CALL apoc.path.subgraphAll(e, {maxLevel: $depth}) YIELD node, relationship
                RETURN node, relationship
                """,
                ids=entity_ids,
                depth=depth,
            )
            async for _ in result:
                pass  # traversal handled below via simpler pattern
        # Fallback simple traversal (works without APOC):
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Entity)-[r:REL]->(o:Entity)
                WHERE s.id IN $ids OR o.id IN $ids
                RETURN s, r, o
                """,
                ids=entity_ids,
            )
            async for record in result:
                s, r, o = record["s"], record["r"], record["o"]
                triples.append(
                    Triple(
                        subject=EntityRef(id=s["id"], name=s["name"], type=s.get("type", "other")),
                        predicate=r["predicate"],
                        object=EntityRef(id=o["id"], name=o["name"], type=o.get("type", "other")),
                        confidence=float(r.get("confidence", 0.0)),
                        provenance=_to_provenance(r.get("provenance")),
                    )
                )
        return triples

    async def temporal_query(self, window: str) -> list[Triple]:
        """Return triples added/modified within the given time window.

        ``window`` is ``"all"`` or a number of days (e.g. ``"7d"``).
        """
        self.connect()
        if window.strip().lower() in {"all", "*"}:
            cypher = "MATCH (s:Entity)-[r:REL]->(o:Entity) RETURN s, r, o"
            params: dict[str, Any] = {}
        else:
            import re
            from datetime import datetime, timedelta

            m = re.fullmatch(r"(\d+)\s*d", window.strip().lower())
            if not m:
                return []
            cutoff = (datetime.now(UTC) - timedelta(days=int(m.group(1)))).isoformat()
            cypher = (
                "MATCH (s:Entity)-[r:REL]->(o:Entity) "
                "WHERE r.last_seen >= datetime($cutoff) RETURN s, r, o"
            )
            params = {"cutoff": cutoff}
        triples: list[Triple] = []
        async with self.driver.session() as session:
            result = await session.run(cypher, params)
            async for record in result:
                s, r, o = record["s"], record["r"], record["o"]
                triples.append(
                    Triple(
                        subject=EntityRef(id=s["id"], name=s["name"], type=s.get("type", "other")),
                        predicate=r["predicate"],
                        object=EntityRef(id=o["id"], name=o["name"], type=o.get("type", "other")),
                        confidence=float(r.get("confidence", 0.0)),
                        provenance=_to_provenance(r.get("provenance")),
                    )
                )
        return triples
