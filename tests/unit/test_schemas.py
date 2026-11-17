import json

import pytest
from pydantic import ValidationError

from ara.schemas import (
    ARAState,
    Chunk,
    Entity,
    EntityRef,
    EvolutionEvent,
    ExperimentProposal,
    Hypothesis,
    Paper,
    Provenance,
    Triple,
)


def test_paper_round_trip() -> None:
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
    data = json.loads(paper.model_dump_json())
    paper_copy = Paper.model_validate(data)
    assert paper == paper_copy
    assert len(paper.chunks) == len(paper_copy.chunks)


def test_entity_literal_validation() -> None:
    Entity(
        id="geneA",
        canonical_name="BRCA1",
        type="gene",
        aliases=["BRCA1"],
        external_ids={"HGNC": "HGNC:123"},
    )
    with pytest.raises(ValidationError):
        Entity(
            id="geneA",
            canonical_name="BRCA1",
            type="invalid_type",
        )


def test_triple_confidence_bounds() -> None:
    prop = Provenance(
        paper_id="PMID:001",
        chunk_id="c1",
        span=0,
        extracted_by="tester",
    )
    t = Triple(
        subject=EntityRef(name="GeneA", id="geneA"),
        predicate="expresses",
        object=EntityRef(name="ProteinX", id="proteinX"),
        confidence=0.95,
        provenance=prop,
    )
    assert t.confidence >= 0.0 and t.confidence <= 1.0

    with pytest.raises(ValidationError):
        Triple(
            subject=EntityRef(name="GeneA", id="geneA"),
            predicate="expresses",
            object=EntityRef(name="ProteinX", id="proteinX"),
            confidence=1.5,
            provenance=prop,
        )


def test_hypothesis_scores() -> None:
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

    with pytest.raises(ValidationError):
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


def test_experiment_required_fields() -> None:
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


def test_evolution_change_type() -> None:
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


def test_ara_state_import() -> None:
    assert isinstance(ARAState, type)
