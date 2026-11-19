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
import os
import re
from pathlib import Path
from typing import Any

from ara.nodes.extraction import extract_relations_node, validate_triples_node
from ara.schemas import ARAState, Chunk, Paper, Triple, coerce_triple
from ara.schemas.predicates import predicate_group

GOLD_PATH = Path(__file__).resolve().parent / "gold" / "sample_triples.jsonl"
GOLD_DIR = Path(__file__).resolve().parent / "gold"
# Non-circular gold: hand-verified triples from REAL PubMed abstracts (raw
# text committed under gold/raw_abstracts/ so the gold is reproducible).
REAL_GOLD_PATH = GOLD_DIR / "real_abstracts.jsonl"
DISTRACTOR_PATH = GOLD_DIR / "distractors.jsonl"
RAW_ABSTRACTS_DIR = GOLD_DIR / "raw_abstracts"

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
    """Normalize an entity/predicate name for matching.

    Case + whitespace folding, plus punctuation stripping (hyphens kept —
    gene/protein symbols like ``gamma-H2AX`` rely on them). Purely lexical:
    never changes which triples match semantically, only how surface forms
    compare (e.g. a trailing "." from an LLM sentence no longer breaks a match).
    """
    text = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"\s+", " ", text)


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


_STOPWORDS = {
    "of",
    "the",
    "a",
    "an",
    "in",
    "to",
    "and",
    "or",
    "by",
    "with",
    "for",
    "on",
    "at",
    "are",
    "is",
    "was",
    "that",
    "which",
    "this",
    "these",
    "their",
}


def _tokens(text: str) -> set[str]:
    """Content tokens of a normalized name (stopwords dropped)."""
    toks = {t for t in normalize(text).split() if t not in _STOPWORDS}
    return toks or {normalize(text)}


def entity_match(a: str, b: str, threshold: float = 0.5) -> bool:
    """Entity-name match: exact after normalization, token Jaccard >= threshold,
    or containment when the shorter name has >= 2 content tokens.

    Purely lexical — handles surface variation ("inhibition of PARP" vs
    "PARP inhibition"; "homologous recombination" inside "DNA double-strand
    break repair by homologous recombination") without changing what the
    triple *means*. Single-token containment is NOT allowed, so "BRCA1" does
    not match "BRCA1 dysfunction" (keeps direction/entity distractors rejected).
    Predicate and direction are NOT fuzzy.
    """
    na, nb = normalize(a), normalize(b)
    if na == nb:
        return True
    ta, tb = _tokens(a), _tokens(b)
    if len(ta & tb) / len(ta | tb) >= threshold:
        return True
    smaller, larger = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return len(smaller) >= 2 and smaller <= larger


def triple_match(p: Triple, g: Triple) -> bool:
    """A predicted triple matches a gold triple iff the predicates are in the
    same canonical match group (see :func:`ara.schemas.predicates.predicate_group`)
    and both entity names match (see :func:`entity_match`)."""
    return (
        predicate_group(p.predicate) == predicate_group(g.predicate)
        and entity_match(p.subject.name, g.subject.name)
        and entity_match(p.object.name, g.object.name)
    )


def prf1(predicted: list[Triple], gold: list[Triple]) -> dict[str, float]:
    """Precision / recall / F1 of *predicted* against *gold*.

    Bipartite (non-consuming) matching via :func:`triple_match`: a gold triple
    counts as recalled if ANY predicted triple matches it, and a predicted
    triple counts as precise if it matches ANY gold triple — so one merged
    prediction ("induce gamma-H2AX and RAD51 foci") can recall two gold
    triples.
    """
    tp_recall = sum(1 for g in gold if any(triple_match(p, g) for p in predicted))
    tp_precision = sum(1 for p in predicted if any(triple_match(p, g) for g in gold))
    n_pred = len(predicted)
    precision = tp_precision / n_pred if n_pred else 0.0
    recall = tp_recall / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def extraction_f1(predicted: list[Triple], gold: list[Triple]) -> float:
    """F1 of *predicted* triples against the *gold* set."""
    return prf1(predicted, gold)["f1"]


def load_raw_abstracts() -> list[Paper]:
    """Build eval Papers from the committed raw abstracts (``raw_abstracts/*.txt``)."""
    papers: list[Paper] = []
    for path in sorted(RAW_ABSTRACTS_DIR.glob("*.txt")):
        pmid = path.stem
        raw = path.read_text(encoding="utf-8")
        title, _, abstract = raw.partition("\n\n")
        abstract = abstract.strip()
        papers.append(
            Paper(
                id=f"PMID:{pmid}",
                source="pubmed",
                title=title.strip(),
                abstract=abstract,
                authors=[],
                year=0,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                full_text=None,
                chunks=[Chunk(text=abstract, paper_id=f"PMID:{pmid}", span=0)],
            )
        )
    return papers


def distractor_rejection_rate(predicted: list[Triple], distractors: list[Triple]) -> float:
    """Fraction of distractor triples the extractor did NOT emit (precision guard).

    Distractors are near-misses (right entities / wrong predicate, or right
    predicate / reversed direction), so :func:`triple_match` — exact predicate,
    directional entities — is exactly what rejects them.
    """
    if not distractors:
        return 1.0
    hits = sum(1 for d in distractors if any(triple_match(p, d) for p in predicted))
    return 1.0 - hits / len(distractors)


async def eval_with_mode(
    mode: Any = "mock", gold_path: Path | str = REAL_GOLD_PATH
) -> dict[str, Any]:
    """Run the extractor in *mode* over the real abstracts and score it.

    Returns ``{"mode", "gold", "n_gold", "n_predicted", "precision",
    "recall", "f1", "distractor_rejection"}``. ``mode="mock"`` is offline;
    ``mode="live"`` needs ``OPENAI_API_KEY`` (and honors ``EVAL_CACHE=1``).
    """
    from ara.config import get_settings

    old = os.environ.get("EXTRACTION_MODE")
    os.environ["EXTRACTION_MODE"] = mode
    get_settings.cache_clear()
    try:
        predicted = await extract_predicted(load_raw_abstracts())
        gold = load_gold(gold_path)
        distractors = load_gold(DISTRACTOR_PATH)
        m = prf1(predicted, gold)
        return {
            "mode": mode,
            "gold": Path(gold_path).name,
            "n_gold": len(gold),
            "n_predicted": len(predicted),
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1"],
            "distractor_rejection": distractor_rejection_rate(predicted, distractors),
        }
    finally:
        if old is None:
            os.environ.pop("EXTRACTION_MODE", None)
        else:
            os.environ["EXTRACTION_MODE"] = old
        get_settings.cache_clear()


__all__ = [
    "GOLD_PATH",
    "GOLD_DIR",
    "REAL_GOLD_PATH",
    "DISTRACTOR_PATH",
    "RAW_ABSTRACTS_DIR",
    "EVAL_PAPERS",
    "eval_papers",
    "load_gold",
    "load_raw_abstracts",
    "normalize",
    "triple_key",
    "extract_predicted",
    "prf1",
    "extraction_f1",
    "distractor_rejection_rate",
    "eval_with_mode",
]
