import pytest
from ara.state import ARAState

from ara.nodes.extraction import (
    extract_entities_node,
    extract_relations_node,
    link_entities_node,
    validate_triples_node,
)


@pytest.mark.asyncio
async def test_extract_entities_node():
    state = ARAState(
        task="ingest pubmed",
        papers=[],
        chunks=[],
        extracted_entities=[],
        extracted_triples=[],
        linked_entities=[],
        valid_triples=[],
        errors=[],
    )
    # add a paper with a chunk containing entity names
    paper = {
        "id": "PMID:001",
        "source": "pubmed",
        "title": "Test",
        "abstract": "GeneA, ProteinX",
        "authors": ["A"],
        "year": 2024,
        "url": None,
        "full_text": "GeneA, ProteinX",
        "chunks": [
            {"text": "GeneA, ProteinX", "paper_id": "PMID:001", "span": 0, "embedding": None}
        ],
    }
    state["papers"] = [paper]
    # run node
    result = await extract_entities_node(state)
    assert "extracted_entities" in result
    assert len(result["extracted_entities"]) > 0


@pytest.mark.asyncio
async def test_extract_relations_node():
    state = ARAState(
        task="ingest pubmed",
        papers=[],
        chunks=[],
        extracted_entities=[],
        extracted_triples=[],
        linked_entities=[],
        valid_triples=[],
        errors=[],
    )
    paper = {
        "id": "PMID:001",
        "source": "pubmed",
        "title": "Test",
        "abstract": "GeneA - expresses - ProteinX",
        "authors": ["A"],
        "year": 2024,
        "url": None,
        "full_text": "GeneA - expresses - ProteinX",
        "chunks": [
            {
                "text": "GeneA - expresses - ProteinX",
                "paper_id": "PMID:001",
                "span": 0,
                "embedding": None,
            }
        ],
    }
    state["papers"] = [paper]
    result = await extract_relations_node(state)
    assert "extracted_triples" in result
    assert len(result["extracted_triples"]) > 0


@pytest.mark.asyncio
async def test_link_entities_node():
    state = ARAState(
        task="ingest pubmed",
        papers=[],
        chunks=[],
        extracted_entities=[],
        extracted_triples=[],
        linked_entities=[],
        valid_triples=[],
        errors=[],
    )
    # add a dummy entity dict
    state["extracted_entities"] = [{"entity": {"name": "p53", "type": "protein", "id": "p53"}}]
    result = await link_entities_node(state)
    assert "linked_entities" in result
    assert len(result["linked_entities"]) > 0
    # verify that resolved name matches expected alias
    assert any(e["entity"].name == "proteinX" for e in result["linked_entities"])


@pytest.mark.asyncio
async def test_validate_triples_node():
    state = ARAState(
        task="ingest pubmed",
        papers=[],
        chunks=[],
        extracted_entities=[],
        extracted_triples=[],
        linked_entities=[],
        valid_triples=[],
        errors=[],
    )
    low_conf = {
        "subject": {"name": "geneA", "type": "gene", "id": "geneA"},
        "predicate": "expresses",
        "object": {"name": "proteinX", "type": "protein", "id": "proteinX"},
        "confidence": 0.5,
        "provenance": {
            "paper_id": "PMID:001",
            "chunk_id": "c1",
            "span": 0,
            "extracted_by": "tester",
        },
    }
    high_conf = {
        "subject": {"name": "geneB", "type": "gene", "id": "geneB"},
        "predicate": "binds",
        "object": {"name": "proteinY", "type": "protein", "id": "proteinY"},
        "confidence": 0.9,
        "provenance": {
            "paper_id": "PMID:001",
            "chunk_id": "c1",
            "span": 0,
            "extracted_by": "tester",
        },
    }
    state["extracted_triples"] = [low_conf, high_conf]
    result = await validate_triples_node(state)
    assert "valid_triples" in result
    assert len(result["valid_triples"]) == 1
    assert result["valid_triples"][0]["confidence"] == 0.9
