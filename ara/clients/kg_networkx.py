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
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import networkx as nx

from ara.clients.kg import KGDelta, KGWriteError
from ara.schemas.entity import EntityRef
from ara.schemas.triple import Provenance, Triple


def _slug(name: str) -> str:
    """Canonical entity id for a name (lower-cased, non-alphanumerics to '_')."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip()).strip("_").lower()
    return slug or "entity"


class NetworkXKnowledgeGraphClient:
    """In‑memory directed graph persisted to a JSON file."""

    def __init__(self, storage_path: str = "kg_store.json"):
        self.storage_path = Path(storage_path)
        self.graph: nx.DiGraph = nx.DiGraph()
        self._pending_snapshot: dict[str, Any] | None = None
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
        """Atomically persist the graph (tmp file + os.replace)."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": [{"id": n, **dict(self.graph.nodes[n])} for n in self.graph.nodes],
            "edges": [
                {"source": u, "target": v, "properties": dict(self.graph.edges[u, v])}
                for u, v in self.graph.edges
            ],
        }
        tmp_path = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        os.replace(tmp_path, self.storage_path)

    # ------------------------------------------------------------------
    # KnowledgeGraphClient protocol
    # ------------------------------------------------------------------
    async def ensure_schema(self) -> None:
        """No schema to create for NetworkX; just reload from disk."""
        self._load()

    async def upsert_triples(self, triples: list[Triple]) -> KGDelta:
        """MERGE semantics: add missing nodes/edges, refresh existing ones.

        Atomic: before mutating, the touched nodes/edges are snapshotted; on
        any failure the snapshot is restored (in-memory graph back to its
        pre-batch state) and :class:`KGWriteError` is raised — nothing is
        persisted. On success the store is saved ONCE, atomically.
        """
        delta: KGDelta = {"added": 0, "updated": 0, "edges": []}
        now = datetime.now(UTC).isoformat()

        node_ids: set[str] = set()
        edge_keys: set[tuple[str, str]] = set()
        for triple in triples:
            subj_id = triple.subject.id or _slug(triple.subject.name)
            obj_id = triple.object.id or _slug(triple.object.name)
            node_ids.update((subj_id, obj_id))
            edge_keys.add((subj_id, obj_id))

        snapshot = self._snapshot_touched(node_ids, edge_keys)
        self._pending_snapshot = snapshot
        try:
            for triple in triples:
                self._apply_triple(triple, now, delta)
        except Exception as exc:
            self._restore_snapshot(snapshot)
            self._pending_snapshot = None
            raise KGWriteError(
                f"NetworkX batch upsert failed; in-memory graph restored "
                f"({len(triples)} triples, 0 persisted): {exc}"
            ) from exc
        self._pending_snapshot = None
        self._save()  # single atomic write per batch
        return delta

    def _apply_triple(self, triple: Triple, now: str, delta: KGDelta) -> None:
        """Apply one triple to the in-memory graph, updating *delta*."""
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
            existing["confidence"] = max(float(existing.get("confidence", 0.0)), triple.confidence)
            delta["updated"] += 1
        delta["edges"].append({"subject": subj_id, "predicate": triple.predicate, "object": obj_id})

    def _snapshot_touched(
        self, node_ids: set[str], edge_keys: set[tuple[str, str]]
    ) -> dict[str, Any]:
        """Capture the current attrs of touched nodes/edges + what is absent."""
        return {
            "nodes": {n: dict(self.graph.nodes[n]) for n in node_ids if self.graph.has_node(n)},
            "edges": {
                e: dict(self.graph.edges[e[0], e[1]])
                for e in edge_keys
                if self.graph.has_edge(e[0], e[1])
            },
            "new_nodes": [n for n in node_ids if not self.graph.has_node(n)],
            "new_edges": [e for e in edge_keys if not self.graph.has_edge(e[0], e[1])],
        }

    def _restore_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Undo a failed batch: remove added nodes/edges, restore old attrs."""
        for u, v in snapshot["new_edges"]:
            if self.graph.has_edge(u, v):
                self.graph.remove_edge(u, v)
        for n in snapshot["new_nodes"]:
            if self.graph.has_node(n):
                self.graph.remove_node(n)
        for n, attrs in snapshot["nodes"].items():
            if self.graph.has_node(n):
                current = self.graph.nodes[n]
                for key in list(current):
                    del current[key]
                current.update(attrs)
        for (u, v), attrs in snapshot["edges"].items():
            if self.graph.has_edge(u, v):
                current = self.graph.edges[u, v]
                for key in list(current):
                    del current[key]
                current.update(attrs)

    async def rollback(self, delta: KGDelta) -> None:
        """Restore the pre-batch snapshot of the last failed upsert."""
        snapshot = self._pending_snapshot
        if snapshot is not None:
            self._restore_snapshot(snapshot)
            self._pending_snapshot = None

    async def resolve_entity(self, name: str, entity_type: str) -> EntityRef:
        """Resolve a name to a canonical slug id (registering the alias).

        In-memory only — the store is persisted once per upsert batch, not
        per entity.
        """
        node_id = _slug(name)
        if node_id not in self.graph:
            self.graph.add_node(node_id, name=name, type=entity_type, aliases=[name])
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
