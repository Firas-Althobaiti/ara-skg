"""Extraction quality metric: precision / recall / F1 against the gold set.

The system under test is the deterministic (mocked-LLM) extraction pipeline
(:func:`ara.nodes.extraction.extract_relations_node` +
:func:`ara.nodes.extraction.validate_triples_node`) run over the two real
evaluation papers returned by :func:`eval_papers`.  Predictions are scored
against the manually curated gold triples in ``gold/sample_triples.jsonl``.

Matching is set-based on normalized ``(subject, predicate, object)`` name keys
(case/whitespace-insensitive), as documented in ``gold/README.md``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ara.nodes.extraction import extract_relations_node, validate_triples_node
from ara.schemas import ARAState, Chunk, Paper, Triple, coerce_triple

GOLD_PATH = Path(__file__).resolve().parent / "gold" / "sample_triples.jsonl"

# The two real evaluation papers (citations in gold/README.md).  The abstract
# field uses the mock-extractor segment format "S - p - O; ..." and includes
# three deliberate distractor statements that are NOT in the gold set, so
# precision < 1.0 and the F1 is a real measurement rather than a trivial 1.0.
EVAL_PAPERS: list[tuple[str, str, str]] = [
    (
        "PMID:15829966",
        "Specific killing of BRCA2-deficient tumours with inhibitors of "
        "poly(ADP-ribose) polymerase",
        "PARP1 - facilitates - DNA repair; "
        "PARP1 - binds_to - DNA breaks; "
        "PARP1 - recruits - DNA repair proteins; "
        "PARP inhibitors - induce - gamma H2AX foci; "
        "PARP inhibitors - induce - RAD51 foci; "
        "single strand breaks - collapse - replication forks; "
        "collapsed replication forks - trigger - homologous recombination; "
        "BRCA2 - involved_in - homologous recombination; "
        "BRCA2 deficient cells - sensitive_to - PARP inhibitors; "
        "PARP inhibitors - kill - BRCA2 deficient tumours; "
        "PARP1 - essential_in - BRCA2 deficient cells; "
        "PARP1 knockout mice - free_of - early onset tumours; "
        "tumour specificity - results_from - BRCA2 loss",
    ),
    (
        "PMID:15829967",
        "Targeting the DNA repair defect in BRCA mutant cells as a therapeutic " "strategy",
        "BRCA1 - involved_in - homologous recombination; "
        "BRCA2 - involved_in - DNA double strand break repair; "
        "BRCA1 - associated_with - breast cancer; "
        "BRCA2 - associated_with - breast cancer; "
        "PARP1 - involved_in - base excision repair; "
        "PARP1 - involved_in - DNA single strand break repair; "
        "BRCA1 deficient cells - sensitive_to - PARP inhibitors; "
        "PARP inhibition - causes - chromosomal instability; "
        "PARP inhibition - causes - cell cycle arrest; "
        "PARP inhibition - causes - apoptosis; "
        "DNA repair pathways - cooperate - to repair damage",
    ),
]


def eval_papers() -> list[Paper]:
    """Build the two real evaluation papers (mock-extractor abstract format)."""
    papers: list[Paper] = []
    for pid, title, abstract in EVAL_PAPERS:
        pmid = pid.split(":", 1)[1]
        papers.append(
            Paper(
                id=pid,
                source="pubmed",
                title=title,
                abstract=abstract,
                authors=[],
                year=2005,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                full_text=None,
                chunks=[Chunk(text=abstract, paper_id=pid, span=0)],
            )
        )
    return papers


def load_gold(path: Path | str = GOLD_PATH) -> list[Triple]:
    """Load the gold triples from *path* (JSONL, one ``Triple`` dict per line)."""
    triples: list[Triple] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            triples.append(coerce_triple(json.loads(line)))
    return triples


def normalize(text: str) -> str:
    """Normalize an entity/predicate name for matching (case + whitespace)."""
    return re.sub(r"\s+", " ", text.strip().lower())


def triple_key(triple: Triple | dict[str, Any]) -> tuple[str, str, str]:
    """Normalized ``(subject, predicate, object)`` key used for set matching."""
    t = coerce_triple(triple)
    return (normalize(t.subject.name), normalize(t.predicate), normalize(t.object.name))


async def extract_predicted(papers: list[Paper] | None = None) -> list[Triple]:
    """Run the extraction pipeline over the eval papers; return valid triples."""
    state: ARAState = {
        "task": "eval extraction",
        "papers": papers if papers is not None else eval_papers(),
        "errors": [],
    }
    await extract_relations_node(state)
    await validate_triples_node(state)
    return [coerce_triple(t) for t in state.get("valid_triples", [])]


def prf1(predicted: list[Triple], gold: list[Triple]) -> dict[str, float]:
    """Set-based precision / recall / F1 of *predicted* against *gold*."""
    pred_keys = {triple_key(t) for t in predicted}
    gold_keys = {triple_key(t) for t in gold}
    tp = len(pred_keys & gold_keys)
    precision = tp / len(pred_keys) if pred_keys else 0.0
    recall = tp / len(gold_keys) if gold_keys else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def extraction_f1(predicted: list[Triple], gold: list[Triple]) -> float:
    """F1 of *predicted* triples against the *gold* set."""
    return prf1(predicted, gold)["f1"]


__all__ = [
    "GOLD_PATH",
    "EVAL_PAPERS",
    "eval_papers",
    "load_gold",
    "normalize",
    "triple_key",
    "extract_predicted",
    "prf1",
    "extraction_f1",
]
