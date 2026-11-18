"""ARA‑SKG command line interface (typer).

Commands
--------
- ``ara ingest``       – fetch/mock papers, extract triples, upsert into the KG
- ``ara query``        – natural-language query over the KG (guarded NL→Cypher)
- ``ara hypothesize``  – generate + ground + rank hypotheses from the KG
- ``ara evolve``       – diff the current KG window against the previous one
- ``ara demo``         – full end-to-end demo (delegates to ``scripts/demo.py``)

All commands default to the offline NetworkX backend (``ARA_KG_BACKEND``,
``ARA_KG_STORE``) and a mocked LLM, so they run without any API key.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
from typing import Any, cast

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ara.config import get_settings
from ara.logging import get_logger
from ara.nodes.evolution import detect_changes_node, summarize_evolution_node, window_triples_node
from ara.nodes.extraction import (
    extract_entities_node,
    extract_relations_node,
    link_entities_node,
    validate_triples_node,
)
from ara.nodes.graph_update import ensure_schema_node, resolve_triples_node, upsert_kg_node
from ara.nodes.hypothesis import (
    critique_hypothesis_node,
    generate_hypotheses_node,
    ground_hypothesis_node,
    rank_hypotheses_node,
)
from ara.nodes.ingestion import ingest_papers
from ara.nodes.query import (
    classify_query_node,
    guard_cypher_node,
    nl2cypher_node,
    run_cypher_node,
    synthesize_answer_node,
)
from ara.schemas import ARAState, coerce_triple

app = typer.Typer(
    help="ARA‑SKG — LangGraph-based Autonomous Research Assistant CLI",
    no_args_is_help=True,
)
console = Console()
logger = get_logger("ara.cli")

REPO_ROOT = Path(__file__).resolve().parent.parent


def _use_kg_store(kg_store: str | None) -> None:
    """Point the NetworkX backend at *kg_store* (and reset the settings cache)."""
    if kg_store:
        os.environ["ARA_KG_BACKEND"] = "networkx"
        os.environ["ARA_KG_STORE"] = str(kg_store)
    else:
        os.environ.setdefault("ARA_KG_BACKEND", "networkx")
    get_settings.cache_clear()


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Attribute-or-key access for Pydantic models and plain dicts alike."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _apply(state: ARAState, update: dict[str, Any]) -> None:
    """Merge a node's partial state (plain dict) into the ARAState TypedDict."""
    state.update(cast(ARAState, update))


def _triple_rows(triples: list[Any], limit: int = 25) -> Table:
    table = Table(title="Knowledge-graph triples", header_style="bold cyan")
    table.add_column("Subject")
    table.add_column("Predicate")
    table.add_column("Object")
    table.add_column("Conf.", justify="right")
    table.add_column("Paper")
    for raw in triples[:limit]:
        t = coerce_triple(raw)
        table.add_row(
            t.subject.name,
            t.predicate,
            t.object.name,
            f"{t.confidence:.2f}",
            t.provenance.paper_id,
        )
    return table


def _hypothesis_table(hypotheses: list[Any]) -> Table:
    table = Table(title="Hypotheses (ranked)", header_style="bold cyan")
    table.add_column("ID")
    table.add_column("Statement", overflow="fold")
    table.add_column("Novelty", justify="right")
    table.add_column("Plausibility", justify="right")
    table.add_column("#Support", justify="right")
    table.add_column("Status")
    for hyp in hypotheses:
        table.add_row(
            str(_get(hyp, "id", "")),
            str(_get(hyp, "statement", "")),
            f"{_get(hyp, 'novelty_score', 0.0):.2f}",
            f"{_get(hyp, 'plausibility_score', 0.0):.2f}",
            str(len(_get(hyp, "supporting", []) or [])),
            str(_get(hyp, "status", "")),
        )
    return table


@app.command()
def ingest(
    query: str = typer.Argument("demo biomedical corpus", help="Search query / task text."),
    source: str = typer.Option("mock", "--source", "-s", help="mock | pubmed | arxiv | pdf"),
    kg_store: str | None = typer.Option(None, "--kg-store", help="NetworkX KG JSON path"),
    persist: bool = typer.Option(False, "--persist", help="Also write chunks to the vector store"),
) -> None:
    """Ingest papers into the KG: fetch → extract → resolve → upsert."""
    _use_kg_store(kg_store)
    logger.info("ingest start", source=source, query=query)
    state = cast(ARAState, {"task": f"ingest {source} {query}", "persist": persist, "errors": []})

    async def _run() -> ARAState:
        _apply(state, await ingest_papers(state))
        for node in (
            extract_entities_node,
            extract_relations_node,
            link_entities_node,
            validate_triples_node,
            resolve_triples_node,
            ensure_schema_node,
            upsert_kg_node,
        ):
            _apply(state, await node(state))
        return state

    final = asyncio.run(_run())
    papers = final.get("papers", [])
    table = Table(
        title=f"Ingested papers (source={final.get('source', source)})", header_style="bold green"
    )
    table.add_column("ID")
    table.add_column("Title", overflow="fold")
    table.add_column("Year", justify="right")
    table.add_column("Chunks", justify="right")
    for paper in papers:
        table.add_row(
            str(_get(paper, "id", "")),
            str(_get(paper, "title", "")),
            str(_get(paper, "year", "")),
            str(len(_get(paper, "chunks", []) or [])),
        )
    console.print(table)
    console.print(_triple_rows(final.get("valid_triples", [])))
    delta = final.get("kg_delta", {})
    if isinstance(delta, dict) and delta:
        console.print(
            Panel(
                f"added={delta.get('added', 0)} updated={delta.get('updated', 0)}",
                title="KG delta",
                border_style="green",
            )
        )
    if final.get("errors"):
        console.print(f"[bold red]errors:[/bold red] {final['errors']}")
        raise typer.Exit(code=1)
    console.print("[bold green]Ingest complete.[/bold green]")


@app.command()
def query(
    question: str = typer.Argument(
        ..., help="Natural-language question, e.g. 'Which entities are in the KG?'"
    ),
    kg_store: str | None = typer.Option(None, "--kg-store", help="NetworkX KG JSON path"),
) -> None:
    """Run a guarded NL→Cypher query against the KG and print the answer."""
    _use_kg_store(kg_store)
    logger.info("query", question=question)
    state: ARAState = {"task": question, "errors": []}

    async def _run() -> ARAState:
        for node in (
            classify_query_node,
            nl2cypher_node,
            guard_cypher_node,
            run_cypher_node,
            synthesize_answer_node,
        ):
            _apply(state, await node(state))
            if state.get("error"):
                break
        return state

    final = asyncio.run(_run())
    if final.get("error"):
        console.print(f"[bold red]Query rejected:[/bold red] {final['error']}")
        raise typer.Exit(code=1)
    rows = final.get("run_result", {}).get("result", [])
    table = Table(title="Query result rows", header_style="bold cyan")
    if rows:
        for key in rows[0]:
            table.add_column(str(key))
        for row in rows[:25]:
            table.add_row(*[str(v) for v in row.values()])
    console.print(table)
    console.print(Panel(str(final.get("final_answer", "")), title="Answer", border_style="green"))


@app.command()
def hypothesize(
    top_k: int = typer.Option(3, "--top-k", "-k", help="Number of hypotheses to generate"),
    kg_store: str | None = typer.Option(None, "--kg-store", help="NetworkX KG JSON path"),
) -> None:
    """Generate, ground and rank hypotheses from the current KG (mocked LLM)."""
    _use_kg_store(kg_store)
    logger.info("hypothesize", top_k=top_k)

    async def _run() -> ARAState:
        client = get_settings().client
        triples = await client.all_triples()  # type: ignore[attr-defined]
        state: ARAState = {
            "task": "hypothesize from KG",
            "valid_triples": [t.model_dump() for t in triples],
            "errors": [],
        }
        for node in (
            generate_hypotheses_node,
            ground_hypothesis_node,
            rank_hypotheses_node,
            critique_hypothesis_node,
        ):
            _apply(state, await node(state))
        return state

    final = asyncio.run(_run())
    hypotheses = final.get("hypotheses", [])[:top_k]
    console.print(_hypothesis_table(hypotheses))
    console.print(f"[dim]critique:[/dim] {final.get('critique', '')}")
    if not hypotheses:
        console.print(
            "[bold yellow]No well-supported hypotheses (need >= 2 supporting triples each).[/bold yellow]"
        )


@app.command()
def evolve(
    window: str = typer.Argument("all", help="Time window, e.g. 'all', '7d', or an ISO date"),
    kg_store: str | None = typer.Option(None, "--kg-store", help="NetworkX KG JSON path"),
) -> None:
    """Diff the current KG window against the previous snapshot and report changes."""
    _use_kg_store(kg_store)
    logger.info("evolve", window=window)

    async def _run() -> ARAState:
        client = get_settings().client
        current = [t.model_dump() for t in await client.all_triples()]  # type: ignore[attr-defined]
        store_path = Path(str(getattr(get_settings(), "ARA_KG_STORE", "kg_store.json")))
        prev_path = store_path.with_suffix(store_path.suffix + ".prev.json")
        prev: list[dict[str, Any]] = []
        if prev_path.exists():
            import json

            prev = json.loads(prev_path.read_text(encoding="utf-8")).get("triples", [])
        state: ARAState = {
            "task": f"evolve window {window}",
            "valid_triples": current,
            "prev_valid_triples": prev,
            "errors": [],
        }
        for node in (window_triples_node, detect_changes_node, summarize_evolution_node):
            _apply(state, await node(state))
        # snapshot current window for the next run
        import json

        prev_path.write_text(
            json.dumps({"window": window, "triples": current}, indent=2), encoding="utf-8"
        )
        return state

    final = asyncio.run(_run())
    events = final.get("evolution_events", [])
    table = Table(title=f"Evolution events (window={window})", header_style="bold magenta")
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
    console.print(table)
    console.print(
        Panel(
            str(final.get("evolution_report", "")), title="Evolution report", border_style="magenta"
        )
    )


@app.command()
def demo(
    out: str = typer.Option("artifacts/demo_report.md", "--out", help="Markdown report path"),
    kg_store: str | None = typer.Option(None, "--kg-store", help="NetworkX KG JSON path"),
) -> None:
    """Run the full end-to-end demo (delegates to scripts/demo.py)."""
    _use_kg_store(kg_store)
    script = REPO_ROOT / "scripts" / "demo.py"
    if not script.exists():
        console.print(f"[bold red]demo script not found:[/bold red] {script}")
        raise typer.Exit(code=2)
    spec = importlib.util.spec_from_file_location("ara_demo_script", script)
    if spec is None or spec.loader is None:
        raise typer.Exit(code=2)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    final = asyncio.run(module.run_demo(out_path=Path(out), kg_store=kg_store))
    if final.get("errors"):
        console.print(f"[bold red]demo errors:[/bold red] {final['errors']}")
        raise typer.Exit(code=1)
    console.print(f"[bold green]Demo finished.[/bold green] Report: {out}")


def main() -> None:
    """Console-script entry point (``ara`` after ``pip install -e .``)."""
    app()


if __name__ == "__main__":
    main()
