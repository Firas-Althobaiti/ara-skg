"""End-to-end ARA‑SKG demo (one command: ``make demo`` / ``python scripts/demo.py``).

Pipeline (NetworkX backend + mocked LLM, fully offline)::

    3 mock papers → extract entities/relations → validate → upsert into KG
        → generate 3 hypotheses → ground → rank → critique
        → propose 1 experiment → validate feasibility
        → evolution diff (current window vs. previous) → report

Prints rich tables to the console and writes ``artifacts/demo_report.md``.
Exits 0 on success, 1 if the state accumulated errors.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make the repo's own `ara` package importable when run as `python scripts/demo.py`.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Default to the offline NetworkX KG backend before any settings are read.
os.environ.setdefault("ARA_KG_BACKEND", "networkx")

from langgraph.graph import END, START, StateGraph  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402

from ara.config import get_settings  # noqa: E402
from ara.logging import get_logger  # noqa: E402
from ara.nodes.evolution import (  # noqa: E402
    detect_changes_node,
    summarize_evolution_node,
    window_triples_node,
)
from ara.nodes.experiment import propose_experiment_node, validate_feasibility_node  # noqa: E402
from ara.nodes.extraction import (  # noqa: E402
    extract_entities_node,
    extract_relations_node,
    link_entities_node,
    validate_triples_node,
)
from ara.nodes.graph_update import (  # noqa: E402
    ensure_schema_node,
    resolve_triples_node,
    upsert_kg_node,
)
from ara.nodes.hypothesis import (  # noqa: E402
    critique_hypothesis_node,
    generate_hypotheses_node,
    ground_hypothesis_node,
    rank_hypotheses_node,
)
from ara.nodes.ingestion import ingest_papers  # noqa: E402
from ara.schemas import ARAState, coerce_triple  # noqa: E402

console = Console()
logger = get_logger("ara.demo")

DEFAULT_OUT = REPO_ROOT / "artifacts" / "demo_report.md"


def build_demo_graph() -> Any:
    """Wire the full demo pipeline as a LangGraph ``StateGraph``."""
    g = StateGraph(ARAState)

    steps = [
        ("ingest", ingest_papers),
        ("extract_entities", extract_entities_node),
        ("extract_relations", extract_relations_node),
        ("link_entities", link_entities_node),
        ("validate_triples", validate_triples_node),
        ("resolve_triples", resolve_triples_node),
        ("ensure_schema", ensure_schema_node),
        ("upsert_kg", upsert_kg_node),
        ("generate_hypotheses", generate_hypotheses_node),
        ("ground_hypotheses", ground_hypothesis_node),
        ("rank_hypotheses", rank_hypotheses_node),
        ("critique_hypotheses", critique_hypothesis_node),
        ("propose_experiment", propose_experiment_node),
        ("validate_experiment", validate_feasibility_node),
        ("evolution_window", window_triples_node),
        ("evolution_detect", detect_changes_node),
        ("evolution_summarize", summarize_evolution_node),
    ]
    for name, fn in steps:
        g.add_node(name, fn)

    g.add_edge(START, steps[0][0])
    for (prev, _), (nxt, _) in zip(steps, steps[1:]):
        g.add_edge(prev, nxt)
    g.add_edge(steps[-1][0], END)

    return g.compile()


def _paper_table(papers: list[Any]) -> Table:
    table = Table(title="1) Ingested papers (mock corpus)", header_style="bold green")
    table.add_column("ID")
    table.add_column("Source")
    table.add_column("Title", overflow="fold")
    table.add_column("Year", justify="right")
    table.add_column("Chunks", justify="right")
    for paper in papers:
        get = paper.get if isinstance(paper, dict) else lambda k, d=None: getattr(paper, k, d)
        table.add_row(
            str(get("id", "")),
            str(get("source", "")),
            str(get("title", "")),
            str(get("year", "")),
            str(len(get("chunks", []) or [])),
        )
    return table


def _triple_table(triples: list[Any]) -> Table:
    table = Table(title="2) Extracted triples → KG", header_style="bold cyan")
    table.add_column("Subject")
    table.add_column("Predicate")
    table.add_column("Object")
    table.add_column("Conf.", justify="right")
    table.add_column("Paper")
    for raw in triples:
        t = coerce_triple(raw)
        table.add_row(
            t.subject.name, t.predicate, t.object.name, f"{t.confidence:.2f}", t.provenance.paper_id
        )
    return table


def _hypothesis_table(hypotheses: list[Any]) -> Table:
    table = Table(title="4) Hypotheses (grounded + ranked)", header_style="bold yellow")
    table.add_column("ID")
    table.add_column("Statement", overflow="fold")
    table.add_column("Novelty", justify="right")
    table.add_column("Plaus.", justify="right")
    table.add_column("#Supp.", justify="right")
    for hyp in hypotheses:
        get = hyp.get if isinstance(hyp, dict) else lambda k, d=None: getattr(hyp, k, d)
        table.add_row(
            str(get("id", "")),
            str(get("statement", "")),
            f"{get('novelty_score', 0.0):.2f}",
            f"{get('plausibility_score', 0.0):.2f}",
            str(len(get("supporting", []) or [])),
        )
    return table


def _experiment_table(exp: Any) -> Table:
    table = Table(title="5) Proposed experiment (top hypothesis)", header_style="bold magenta")
    get = exp.get if isinstance(exp, dict) else lambda k, d=None: getattr(exp, k, d)
    table.add_column("Field")
    table.add_column("Value", overflow="fold")
    for field in (
        "id",
        "hypothesis_id",
        "assay",
        "model_system",
        "controls",
        "readouts",
        "expected_outcomes",
        "risks",
        "citations",
    ):
        value = get(field, "")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        table.add_row(field, str(value))
    return table


def _evolution_table(events: list[dict]) -> Table:
    table = Table(
        title="6) Evolution events (current window vs. previous)", header_style="bold blue"
    )
    table.add_column("Type")
    table.add_column("Entity")
    table.add_column("Before")
    table.add_column("After")
    for ev in events[:25]:
        table.add_row(
            str(ev.get("change_type")),
            str(ev.get("entity_id")),
            str(ev.get("before")),
            str(ev.get("after")),
        )
    return table


def _write_report(final: dict, out_path: Path, kg_stats: dict[str, int]) -> None:
    """Write ``artifacts/demo_report.md`` summarising the whole run."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    papers = final.get("papers", [])
    triples = final.get("valid_triples", [])
    hypotheses = final.get("hypotheses", [])
    experiment = final.get("experiment")
    events = final.get("evolution_events", [])
    delta = final.get("kg_delta", {})
    lines: list[str] = [
        "# ARA‑SKG Demo Report",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        "- Backend: NetworkX (JSON store) — `ARA_KG_BACKEND=networkx`",
        "- LLM: mocked (deterministic extractor / hypothesis generator) — no API key needed",
        f"- KG store: `{get_settings().ARA_KG_STORE}`",
        f"- KG size after run: {kg_stats.get('nodes', 0)} nodes / {kg_stats.get('edges', 0)} edges",
        "",
        "## 1) Ingested papers",
        "",
        "| ID | Source | Title | Year | Chunks |",
        "|---|---|---|---|---|",
    ]
    for paper in papers:
        get = paper.get if isinstance(paper, dict) else lambda k, d=None: getattr(paper, k, d)
        lines.append(
            f"| {get('id','')} | {get('source','')} | {get('title','')} | {get('year','')} | {len(get('chunks',[]) or [])} |"
        )
    lines += [
        "",
        "## 2) Extracted triples → knowledge graph",
        "",
        "| Subject | Predicate | Object | Confidence | Paper |",
        "|---|---|---|---|---|",
    ]
    for raw in triples:
        t = coerce_triple(raw)
        lines.append(
            f"| {t.subject.name} | {t.predicate} | {t.object.name} | {t.confidence:.2f} | {t.provenance.paper_id} |"
        )
    if isinstance(delta, dict) and delta:
        lines += [
            "",
            f"KG delta: **added={delta.get('added', 0)}**, **updated={delta.get('updated', 0)}**",
        ]
    lines += [
        "",
        "## 3) KG upsert",
        "",
        f"- added: {delta.get('added', 0) if isinstance(delta, dict) else 'n/a'}",
        f"- updated: {delta.get('updated', 0) if isinstance(delta, dict) else 'n/a'}",
        "",
    ]
    lines += [
        "## 4) Hypotheses (grounded + ranked)",
        "",
        "| ID | Statement | Novelty | Plausibility | #Supporting |",
        "|---|---|---|---|---|",
    ]
    for hyp in hypotheses:
        get = hyp.get if isinstance(hyp, dict) else lambda k, d=None: getattr(hyp, k, d)
        lines.append(
            f"| {get('id','')} | {get('statement','')} | {get('novelty_score',0.0):.2f} | {get('plausibility_score',0.0):.2f} | {len(get('supporting',[]) or [])} |"
        )
    lines += ["", f"Critique: {final.get('critique', '')}", ""]
    if experiment:
        get = (
            experiment.get
            if isinstance(experiment, dict)
            else lambda k, d=None: getattr(experiment, k, d)
        )
        lines += [
            "## 5) Proposed experiment",
            "",
            f"- **id**: {get('id','')}",
            f"- **hypothesis**: {get('hypothesis_id','')}",
            f"- **assay**: {get('assay','')}",
            f"- **model system**: {get('model_system','')}",
            f"- **controls**: {', '.join(str(c) for c in (get('controls',[]) or []))}",
            f"- **readouts**: {', '.join(str(r) for r in (get('readouts',[]) or []))}",
            f"- **expected outcomes**: {', '.join(str(o) for o in (get('expected_outcomes',[]) or []))}",
            f"- **risks**: {', '.join(str(r) for r in (get('risks',[]) or []))}",
            f"- **citations**: {', '.join(str(c) for c in (get('citations',[]) or []))}",
            "",
        ]
    lines += ["## 6) Evolution report", "", str(final.get("evolution_report", "")), ""]
    lines += [
        "## Reproduce",
        "",
        "```bash",
        "make install",
        "make demo        # == python scripts/demo.py",
        "```",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


async def run_demo(out_path: Path | str = DEFAULT_OUT, kg_store: str | None = None) -> dict:
    """Run the full demo pipeline; returns the final ``ARAState``.

    Prints rich tables and writes the markdown report to *out_path*.
    """
    if kg_store:
        os.environ["ARA_KG_STORE"] = str(kg_store)
    os.environ.setdefault("ARA_KG_STORE", str(REPO_ROOT / "artifacts" / "demo_kg.json"))
    get_settings.cache_clear()

    logger.info("demo started")
    state: ARAState = {
        "task": "demo: ingest mock corpus, build KG, hypothesize, propose experiment, report evolution",
        "errors": [],
    }
    app = build_demo_graph()
    final = await app.ainvoke(state)
    final = dict(final)

    kg_stats: dict[str, int] = {}
    try:
        kg_stats = get_settings().client.stats()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - stats are best-effort for the report
        kg_stats = {}

    console.print(
        Panel("ARA‑SKG end-to-end demo (NetworkX backend, mocked LLM)", border_style="cyan")
    )
    console.print(_paper_table(final.get("papers", [])))
    console.print(_triple_table(final.get("valid_triples", [])))
    delta = final.get("kg_delta", {})
    if isinstance(delta, dict) and delta:
        console.print(
            Panel(
                f"added={delta.get('added', 0)}  updated={delta.get('updated', 0)}  "
                f"KG now: {kg_stats.get('nodes', '?')} nodes / {kg_stats.get('edges', '?')} edges",
                title="3) KG upsert",
                border_style="cyan",
            )
        )
    console.print(_hypothesis_table(final.get("hypotheses", [])))
    console.print(f"[dim]critique:[/dim] {final.get('critique', '')}")
    if final.get("experiment"):
        console.print(_experiment_table(final["experiment"]))
    console.print(_evolution_table(final.get("evolution_events", [])))

    out = Path(out_path)
    _write_report(final, out, kg_stats)
    console.print(Panel(f"Report written to {out}", title="Done", border_style="green"))
    logger.info("demo finished", errors=final.get("errors", []))
    return final


def main() -> int:
    """Console entry: run the demo, exit 0 on success."""
    final = asyncio.run(run_demo())
    return 0 if not final.get("errors") else 1


if __name__ == "__main__":
    sys.exit(main())
