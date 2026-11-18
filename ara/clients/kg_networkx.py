"""NetworkX‑backed KnowledgeGraphClient (fallback / offline / demo backend).

The graph is an in-memory ``networkx.DiGraph`` persisted to a JSON file, so
the demo and the CLI work end-to-end without a running Neo4j instance.

Persistence format::

    {"nodes": [{"id": ..., "name": ..., "type": ..., ...}],
     "edges": [{"source": ..., "target": ..., "properties": {...}}]}

Upserts are idempotent: re-inserting an existing edge only refreshes its
properties and is reported as ``updated`` (not ``added``).
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import networkx as nx

from ara.schemas.entity import EntityRef
from ara.schemas.triple import Provenance, Triple

KGDelta = dict[str, Any]  # simple delta representation


def _slug(name: str) -> str:
    """Canonical entity id for a name (lower-cased, non-alphanumerics to '_')."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip()).strip("_").lower()
    return slug or "entity"


class NetworkXKnowledgeGraphClient:
    """In‑memory directed graph persisted to a JSON file."""

    def __init__(self, storage_path: str = "kg_store.json"):
        self.storage_path = Path(storage_path)
        self.graph: nx.DiGraph = nx.DiGraph()
        self._load()

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        self.graph = nx.DiGraph()
        for node in data.get("nodes", []):
            node_id = node["id"]
            props = {k: v for k, v in node.items() if k != "id"}
            self.graph.add_node(node_id, **props)
        for edge in data.get("edges", []):
            self.graph.add_edge(edge["source"], edge["target"], **edge.get("properties", {}))

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": [{"id": n, **dict(self.graph.nodes[n])} for n in self.graph.nodes],
            "edges": [
                {"source": u, "target": v, "properties": dict(self.graph.edges[u, v])}
                for u, v in self.graph.edges
            ],
        }
        self.storage_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # ------------------------------------------------------------------
    # KnowledgeGraphClient protocol
    # ------------------------------------------------------------------
    async def ensure_schema(self) -> None:
        """No schema to create for NetworkX; just reload from disk."""
        self._load()

    async def upsert_triples(self, triples: list[Triple]) -> KGDelta:
        """MERGE semantics: add missing nodes/edges, refresh existing ones."""
        delta: KGDelta = {"added": 0, "updated": 0, "edges": []}
        now = datetime.now(UTC).isoformat()
        for triple in triples:
            subj, obj = triple.subject, triple.object
            subj_id = subj.id or _slug(subj.name)
            obj_id = obj.id or _slug(obj.name)
            for ref, node_id in ((subj, subj_id), (obj, obj_id)):
                if node_id not in self.graph:
                    self.graph.add_node(
                        node_id,
                        name=ref.name,
                        type=ref.type,
                        aliases=[ref.name],
                    )
                    delta["added"] += 1
            edge_key = (subj_id, obj_id)
            props = {
                "predicate": triple.predicate,
                "confidence": triple.confidence,
                "provenance": triple.provenance.model_dump(),
                "last_seen": now,
            }
            if not self.graph.has_edge(*edge_key):
                props["first_seen"] = now
                self.graph.add_edge(*edge_key, **props)
                delta["added"] += 1
            else:
                existing = self.graph.edges[edge_key]
                existing.update(props)
                existing["confidence"] = max(
                    float(existing.get("confidence", 0.0)), triple.confidence
                )
                delta["updated"] += 1
            delta["edges"].append(
                {"subject": subj_id, "predicate": triple.predicate, "object": obj_id}
            )
        self._save()
        return delta

    async def resolve_entity(self, name: str, entity_type: str) -> EntityRef:
        """Resolve a name to a canonical slug id (registering the alias)."""
        node_id = _slug(name)
        if node_id not in self.graph:
            self.graph.add_node(node_id, name=name, type=entity_type, aliases=[name])
            self._save()
        return EntityRef(name=name, type=entity_type, id=node_id)

    async def query_cypher(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a *minimal read-only subset* of Cypher.

        Supports single-node patterns such as::

            MATCH (n:Entity) RETURN n.name AS name, n.id AS id

        Anything else raises ``NotImplementedError`` — use the Neo4j backend
        for full Cypher support.
        """
        if not re.search(r"\bMATCH\s*\(\s*\w+(?::\w+)?\s*\)", cypher, re.IGNORECASE):
            raise NotImplementedError(
                "NetworkX client supports only simple 'MATCH (n[:Label]) RETURN ...' patterns"
            )
        match = re.search(r"\bRETURN\s+(.+)$", cypher, re.IGNORECASE | re.DOTALL)
        if not match:
            raise NotImplementedError("NetworkX client requires a RETURN clause")
        fields = [f.strip() for f in match.group(1).split(",")]
        rows: list[dict[str, Any]] = []
        for node_id, attrs in self.graph.nodes(data=True):
            row: dict[str, Any] = {}
            for field in fields:
                m = re.match(r"\w+\.(\w+)(?:\s+AS\s+(\w+))?$", field, re.IGNORECASE)
                if not m:
                    raise NotImplementedError(f"Unsupported RETURN field: {field!r}")
                prop, alias = m.group(1), m.group(2)
                value = node_id if prop == "id" else attrs.get(prop)
                row[alias or prop] = value
            rows.append(row)
        return rows

    async def subgraph(self, entity_ids: list[str], depth: int = 2) -> list[Triple]:
        """All triples reachable from *entity_ids* up to *depth* hops."""
        seen_nodes: set[str] = set()
        frontier = {eid for eid in entity_ids if eid in self.graph}
        for _ in range(max(depth, 0)):
            new_frontier: set[str] = set()
            for node in frontier:
                if node in seen_nodes:
                    continue
                seen_nodes.add(node)
                new_frontier.update(self.graph.successors(node))
                new_frontier.update(self.graph.predecessors(node))
            frontier = new_frontier - seen_nodes
        return [
            self._edge_to_triple(u, v, attrs)
            for u, v, attrs in self.graph.edges(data=True)
            if u in seen_nodes or v in seen_nodes
        ]

    async def temporal_query(self, window: str) -> list[Triple]:
        """Triples whose ``last_seen`` falls inside *window*.

        ``window`` is ``"all"``, a number of days (e.g. ``"7d"``), or an ISO
        date used as an inclusive lower bound.
        """
        triples: list[Triple] = []
        for u, v, attrs in self.graph.edges(data=True):
            last_seen = attrs.get("last_seen")
            if window.strip().lower() in {"all", "*"}:
                triples.append(self._edge_to_triple(u, v, attrs))
                continue
            if not last_seen:
                continue
            try:
                ts = datetime.fromisoformat(str(last_seen))
            except ValueError:
                continue
            m = re.fullmatch(r"(\d+)\s*d", window.strip().lower())
            if m:
                cutoff = datetime.now(UTC) - timedelta(days=int(m.group(1)))
                if ts >= cutoff:
                    triples.append(self._edge_to_triple(u, v, attrs))
            else:
                try:
                    cutoff = datetime.fromisoformat(window.strip())
                except ValueError:
                    continue
                if ts >= cutoff:
                    triples.append(self._edge_to_triple(u, v, attrs))
        return triples

    # ------------------------------------------------------------------
    # extra helpers (not part of the protocol)
    # ------------------------------------------------------------------
    async def all_triples(self) -> list[Triple]:
        """Return every edge in the graph as a :class:`Triple`."""
        return [self._edge_to_triple(u, v, attrs) for u, v, attrs in self.graph.edges(data=True)]

    def stats(self) -> dict[str, int]:
        """Node/edge counts for reporting."""
        return {"nodes": self.graph.number_of_nodes(), "edges": self.graph.number_of_edges()}

    def _edge_to_triple(self, u: str, v: str, attrs: dict[str, Any]) -> Triple:
        subj_attrs = self.graph.nodes[u]
        obj_attrs = self.graph.nodes[v]
        prov = attrs.get("provenance") or {}
        return Triple(
            subject=EntityRef(
                id=u, name=subj_attrs.get("name", u), type=subj_attrs.get("type", "other")
            ),
            predicate=attrs.get("predicate", "related_to"),
            object=EntityRef(
                id=v, name=obj_attrs.get("name", v), type=obj_attrs.get("type", "other")
            ),
            confidence=float(attrs.get("confidence", 0.0)),
            provenance=(
                Provenance.model_validate(prov)
                if prov
                else Provenance(
                    paper_id="unknown", chunk_id="0", span=0, extracted_by="networkx_store"
                )
            ),
        )
