from typing import Dict, Any
from ara.state import ARAState
from ara.schemas.entity import Entity, EntityRef
from ara.schemas.triple import Triple, Provenance
from ara.schemas.paper import Paper, Chunk
from ara.clients.entity_linking import EntityLinkingClient
import asyncio

async def extract_entities_node(state: ARAState) -> Dict[str, Any]:
    """
    Extract entities from paper text (chunks). For demonstration we treat each chunk
    as containing a comma‑separated list of entity names.
    In a production system this would call an LLM with ``SYSTEM_EXTRACT_ENTITIES.
    """
    extracted = []
    for paper in state.get("papers", []):
        for chunk in paper.chunks:
            # naive parsing: split by commas, strip whitespace
            names = [n.strip() for n in chunk.text.split(",") if n.strip()]
            for name in names:
                entity_ref = EntityRef(name=name, type="other", id=name)
                extracted.append({"entity": entity_ref, "source_chunk": chunk.text[:30]})
    state["extracted_entities"] = extracted
    return state


async def extract_relations_node(state: ARAState) -> Dict[str, Any]:
    """
    Extract triples (subject, predicate, object) from text.
    For demo we treat each chunk's text as containing triples separated by ';'
    and each triple as ``subject - predicate - object.
    """
    triples = []
    for paper in state.get("papers", []):
        for chunk in paper.chunks:
            parts = [p.strip() for p in chunk.text.split(";") if p.strip()]
            for part in parts:
                # naive split by " - "
                segments = [s.strip() for s in part.split("-") if s.strip()]
                if len(segments) == 3:
                    subj, pred, obj = segments
                    subj_ref = EntityRef(name=subj, type="other", id=subj)
                    obj_ref = EntityRef(name=obj, type="other", id=obj)
                    triple = Triple(
                        subject=subj_ref,
                        predicate=pred,
                        object=obj_ref,
                        confidence=0.8,
                        provenance=Provenance(
                            paper_id=paper.id,
                            chunk_id=chunk.span,
                            span=0,
                            extracted_by="extract_relations_node",
                        ),
                    )
                    triples.append(triple)
    state["extracted_triples"] = triples
    return state


async def link_entities_node(state: ARAState) -> Dict[str, Any]:
    """
    Resolve entity names to canonical IDs using the EntityLinkingClient.
    """
    linker = EntityLinkingClient()
    if "extracted_entities" not in state:
        state["extracted_entities"] = []
    linked = []
    for ent in state["extracted_entities"]:
        entity_ref = ent["entity"]
        resolved = await linker.link_entity(entity_ref.name, entity_ref.type)
        linked.append({"entity": resolved, "source": entity_ref.name})
    state["linked_entities"] = linked
    return state


async def validate_triples_node(state: ARAState) -> Dict[str, Any]:
    """
    Critic: keep only triples with confidence >= 0.7 and valid provenance.
    """
    valid = []
    for triple in state.get("extracted_triples", []):
        if triple.confidence >= 0.7 and triple.provenance is not None:
            valid.append(triple)
    state["valid_triples"] = valid
    return state


__all__ = [
    "extract_entities_node",
    "extract_relations_node",
    "link_entities_node",
    "validate_triples_node",
]
