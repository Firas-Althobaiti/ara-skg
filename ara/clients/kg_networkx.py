"""NetworkX‑backed KnowledgeGraphClient (fallback / test implementation)."""

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from ara.schemas.triple import Triple
from ara.schemas.entity import EntityRef
from ara.schemas.provenance import Provenance

KGDelta = Dict[str, Any]  # simple delta representation


class NetworkXKnowledgeGraphClient:
    """In‑memory graph persisted to a JSON file."""

    def __init__(self, storage_path: str = "kg_store.json"):
        self.storage_path = Path(storage_path)
        self.graph = None  # type: nx.DiGraph | None
        self._load()

    def _load(self):
        if self.storage_path.exists():
            data = json.loads(self.storage_path.read_text())
            # placeholder – real code would rebuild an nx.Graph
            self.graph = {}
        else:
            self.graph = {}

    def _save(self):
        data = {
            "nodes": [
                {"id": n, "properties": self.graph[n].copy()}
                for n in self.graph
            ],
            "edges": [
                {"source": u, "target": v, "properties": self.graph[(u, v)].copy()}
                for u, v in self.graph
            ],
        }
        self.storage_path.write_text(json.dumps(data))

    async def ensure_schema(self) -> None:
        self._load()

    async def upsert_triples(self, triples: List[Triple]) -> KGDelta:
        delta = {"added": 0, "updated": 0}

        async def _run():
            for triple in triples:
                subj = triple.subject
                obj = triple.object

                # Ensure subject node exists
                if subj.id not in self.graph:
                    self.graph[subj.id] = {
                        "name": subj.name,
                        "type": subj.type,
                        "aliases": subj.aliases,
                        "external_ids": subj.external_ids,
                    }
                    delta["added"] += 1

                # Ensure object node exists
                if obj.id not in self.graph:
                    self.graph[obj.id] = {
                        "name": obj.name,
                        "type": obj.type,
                        "aliases": obj.aliases,
                        "external_ids": obj.external_ids,
                    }
                    delta["added"] += 1

                # Add edge if not present
                if (subj.id, obj.id) not in self.graph:
                    self.graph[(subj.id, obj.id)] = {
                        "predicate": triple.predicate,
                        "confidence": triple.confidence,
                        "provenance": triple.provenance.dict(),
                    }
                    delta["added"] += 1
                else:
                    delta["updated"] += 1

        await asyncio.to_thread(self._save)
        return delta

    async def resolve_entity(self, name: str, entity_type: str) -> EntityRef:
        return EntityRef(name=name, type=entity_type, id=name)

    async def query_cypher(self, cypher: str, params: dict | None = None) -> List[dict]:
        raise NotImplementedError("Cypher queries not supported by NetworkX client")

    async def subgraph(self, entity_ids: List[str], depth: int = 2) -> List[Triple]:
        raise NotImplementedError

    async def temporal_query(self, window: str) -> List[Triple]:
        raise NotImplementedError

    async def ensure_schema(self) -> None:
        self._load()
