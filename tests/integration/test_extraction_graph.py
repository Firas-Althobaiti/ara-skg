import asyncio
from ara.state import ARAState
from ara.graphs.extraction import build_extraction_graph
from ara.nodes.extraction import (
    extract_entities_node,
    extract_relations_node,
    link_entities_node,
    validate_triples_node,
)

@pytest.mark.asyncio
async def test_extraction_graph_flow():
    # Build the graph (ensures imports work)
    graph = build_extraction_graph()
    # Create a simple state with a paper and a chunk containing a triple
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
            {"text": "GeneA - expresses - ProteinX", "paper_id": "PMID:001", "span": 0, "embedding": None}
        ],
    }
    # Build a minimal state dict (the Graph expects ARAState, but we can feed a dict)
    state = {
        "task": "ingest pubmed",
        "papers": [paper],
        "chunks": paper["chunks"],
        "extracted_entities": [],
        "extracted_triples": [],
        "linked_entities": [],
        "valid_triples": [],
        "errors": [],
    }
    # Execute the nodes in order (simulating the graph)
    await extract_entities_node(state)
    await extract_relations_node(state)
    await link_entities_node(state)
    await validate_triples_node(state)
    # After validation we should have exactly one valid triple
    assert len(state["valid_triples"]) == 1
    assert state["valid_triples"][0]["confidence"] == 0.9
