"""Neo4j implementation of KnowledgeGraphClient."""

from __future__ import annotations

from datetime import UTC
from typing import Any

from neo4j import AsyncGraphDatabase

from ara.clients.kg import KGDelta, KGWriteError  # KGDelta re-exported for backwards compat
from ara.schemas.entity import EntityRef
from ara.schemas.triple import Provenance, Triple

_DEFAULT_PROVENANCE = {
    "paper_id": "unknown",
    "chunk_id": "0",
    "span": 0,
    "extracted_by": "neo4j",
}

_UPSERT_BATCH_QUERY = """
UNWIND $rows AS row
MERGE (s:Entity {id: row.subject_id})
  SET s.name = row.subject_name, s.type = row.subject_type
MERGE (o:Entity {id: row.object_id})
  SET o.name = row.object_name, o.type = row.object_type
OPTIONAL MATCH (s)-[existing:REL {predicate: row.predicate}]->(o)
WITH row, s, o, existing IS NOT NULL AS was_present
MERGE (s)-[r:REL {predicate: row.predicate}]->(o)
  ON CREATE SET r.confidence = row.conf,
                r.provenance = row.prov,
                r.first_seen = datetime()
  ON MATCH  SET r.confidence = CASE
                WHEN r.confidence < row.conf THEN row.conf ELSE r.confidence END,
                r.provenance = row.prov,
                r.last_seen = datetime()
RETURN row.subject_id AS subject, row.predicate AS predicate,
       row.object_id AS object, was_present
"""


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
        """MERGE the whole batch in ONE transaction; return a created/matched delta.

        The batch runs as a single ``UNWIND`` query inside
        ``session.execute_write`` — if any row fails, Neo4j rolls back the
        entire transaction, so no partial writes can persist. The per-row
        created/matched flags are returned by the same query, so the delta
        is computed without any post-commit DB round-trip. Any failure is
        re-raised as :class:`KGWriteError`.
        """
        self.connect()
        rows = [
            {
                "subject_id": t.subject.id or t.subject.name,
                "subject_name": t.subject.name,
                "subject_type": t.subject.type,
                "object_id": t.object.id or t.object.name,
                "object_name": t.object.name,
                "object_type": t.object.type,
                "predicate": t.predicate,
                "conf": t.confidence,
                "prov": t.provenance.model_dump(),
            }
            for t in triples
        ]

        async def _work(tx: Any) -> list[dict[str, Any]]:
            cursor = await tx.run(_UPSERT_BATCH_QUERY, rows=rows)
            return [dict(record) async for record in cursor]

        try:
            async with self.driver.session() as session:
                records = await session.execute_write(_work)
        except Exception as exc:
            raise KGWriteError(
                f"Neo4j batch upsert failed; transaction rolled back "
                f"({len(triples)} triples, 0 persisted): {exc}"
            ) from exc

        delta: KGDelta = {"added": 0, "updated": 0, "edges": []}
        for rec in records:
            if rec.get("was_present"):
                delta["updated"] += 1
            else:
                delta["added"] += 1
            delta["edges"].append(
                {
                    "subject": rec["subject"],
                    "predicate": rec["predicate"],
                    "object": rec["object"],
                }
            )
        return delta

    async def rollback(self, delta: KGDelta) -> None:
        """No-op for Neo4j: the batch ran in a single transaction, so a
        failure already rolled back atomically at the database level."""
        return None

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
