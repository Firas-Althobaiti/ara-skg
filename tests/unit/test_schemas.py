import json
from ara.schemas import (
    Paper,
    Chunk,
    Entity,
    EntityRef,
    Triple,
    Provenance,
    Hypothesis,
    ExperimentProposal,
    EvolutionEvent,
    ARAState,
)


def test_paper_round_trip():
    paper = Paper(
        id="PMID:12345",
        source="pubmed",
        title="Test Paper",
        abstract="A short abstract.",
        authors=["Alice", "Bob"],
        year=2024,
        url="https://example.com",
        chunks=[
            Chunk(
                text="Some text.",
                paper_id="PMID:12345",
                span=0,
                embedding=[0.1, 0.2],
            )
        ],
    )
    # Serialize then deserialize
    data = json.loads(paper.json())
    paper_copy = Paper.parse_obj(data)
    assert paper == paper_copy
    assert len(paper.chunks) == len(paper_copy.chunks)


def test_entity_literal_validation():
    # Valid entity
    Entity(
        id="geneA",
        canonical_name="BRCA1",
        type="gene",
        aliases=["BRCA1"],
        external_ids={"HGNC": "HGNC:123"},
    )
    # Invalid type should raise
    import pytest

    with pytest.raises(Exception):
        Entity(
            id="geneA",
            canonical_name="BRCA1",
            type="invalid_type",  # not in Literal list
        )


def test_triple_confidence_bounds():
    prop = Provenance(
        paper_id="PMID:001",
        chunk_id="c1",
        span=0,
        extracted_by="tester",
    )
    # Valid confidence
    t = Triple(
        subject=EntityRef(name="GeneA", id="geneA"),
        predicate="expresses",
        object=EntityRef(name="ProteinX", id="proteinX"),
        confidence=0.95,
        provenance=prop,
    )
    assert t.confidence >= 0.0 and t.confidence <= 1.0

    # Invalid confidence should raise
    import pytest

    with pytest.raises(Exception):
        Triple(
            subject=EntityRef(name="GeneA", id="geneA"),
            predicate="expresses",
            object=EntityRef(name="ProteinX", id="proteinX"),
            confidence=1.5,  # out of range
            provenance=prop,
        )


def test_hypothesis_scores():
    hyp = Hypothesis(
        id="h1",
        statement="GeneA drives diseaseB",
        mechanism="activation",
        entities=["geneA", "diseaseB"],
        supporting=[],
        contradicting=[],
        novelty_score=0.7,
        plausibility_score=0.6,
        status="proposed",
    )
    assert 0.0 <= hyp.novelty_score <= 1.0
    assert 0.0 <= hyp.plausibility_score <= 1.0
    # Invalid scores raise
    import pytest

    with pytest.raises(Exception):
        Hypothesis(
            id="h1",
            statement="test",
            mechanism="test",
            entities=[],
            supporting=[],
            contradicting=[],
            novelty_score=-0.1,
            plausibility_score=1.2,
        )


def test_experiment_required_fields():
    hyp_id = "h1"
    exp = ExperimentProposal(
        id="exp1",
        hypothesis_id=hyp_id,
        assay="cell_line_treatment",
        model_system="human_cells",
        controls=["vehicle"],
        readouts=["viability"],
        expected_outcomes=["increased_viability"],
        risks=[],
        citations=[],
    )
    assert exp.id is not None
    assert exp.hypothesis_id == hyp_id


def test_evolution_change_type():
    ev = EvolutionEvent(
        window="2023-01/2024-01",
        entity_id="geneA",
        change_type="emerging",
        before="absent",
        after="present",
        evidence=[],
    )
    assert ev.change_type in [
        "emerging",
        "fading",
        "renamed",
        "relation_shift",
    ]


def test_ara_state_import():
    # Import should not raise and state should be a TypedDict
    from ara.schemas.state import ARAState
    assert isinstance(ARAState, type)
