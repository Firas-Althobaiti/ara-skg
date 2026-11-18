# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — coming in v1.1+

### Fixed
- PubMed client: replaced the N+1 esummary loop (which read non-existent
  `article-title` keys and stored `"Placeholder abstract."`) with one
  esearch + ONE batched `efetch rettype=abstract&retmode=xml` parsed via
  stdlib ElementTree — real titles, multi-section abstracts, authors, year,
  DOI lookup. Zero hits now raise `ValueError` instead of silently
  returning an empty list (#12).
- arXiv client: query params are now URL-encoded via httpx `params` (spaces
  and `&` no longer break the URL); the Atom feed is parsed for real
  `<summary>` abstracts, normalized titles, authors, published year, and
  version-stripped ids (`…v2` removed) (#12).
- Both clients retry individual HTTP calls (429/5xx/transport errors) with
  tenacity exponential backoff + jitter, 4 attempts (`ara/clients/_retry.py`);
  `NCBI_API_KEY` is supported via params and raises the NCBI limit to
  10 req/s (#12).

- Wire the real LLM (`ara.llm.get_llm` + structured outputs) into the extraction,
  hypothesis, query and evolution nodes; re-baseline the eval thresholds
  (F1 >= 0.6, grounding == 1.0) against real extraction output.
- Grow the eval gold set beyond 2 papers / 21 triples before using F1 as a
  release gate.
- Full Cypher support on the NetworkX backend (currently a read-only
  `MATCH ... RETURN ...` subset; full Cypher requires Neo4j).
- Real Neo4j end-to-end run in CI (seed idempotency is currently verified
  against the NetworkX client only).

## [1.0.0] — 2026-11-18

First public release. Phases M0–M13 complete: working LangGraph agent,
two KG backends, CLI + offline demo, measurable eval harness, docs site.

### Added

- **Core framework (M0–M2)** — `pyproject.toml` packaging, typed settings
  (`ara/config.py`, env-var driven), Pydantic schemas (`ara/schemas/`),
  structured logging (`ara/logging.py`), LLM factory (`ara/llm.py`), and
  clients for PubMed, arXiv, PDF, vector store (Chroma) and Neo4j
  (`ara/clients/`).
- **Ingestion subgraph (M3)** — `route_sources → fetch_papers → chunk_papers →
  persist_chunks`, with mock / PubMed / arXiv / PDF sources.
- **Extraction subgraph (M4)** — `extract_entities → extract_relations →
  link_entities → validate_triples`; every triple carries provenance
  (paper_id, chunk_id, span, extracted_by).
- **Graph update subgraph (M5)** — canonical entity resolution, schema
  enforcement, MERGE-semantics upsert with rollback on error; two
  interchangeable backends behind the `KnowledgeGraphClient` protocol:
  offline NetworkX/JSON (`kg_networkx.py`) and Neo4j (`neo4j.py`).
- **Query subgraph (M6)** — guarded NL→Cypher (read-only enforced by a guard
  prompt), execution, and evidence-backed answer synthesis.
- **Hypothesis subgraph (M7)** — generate 3–5 hypotheses, ground each in ≥ 2
  provenance-linked triples, rank by novelty + plausibility, critique.
- **Experiment subgraph (M8)** — propose a concrete experiment for the top
  hypothesis and validate feasibility.
- **Evolution subgraph (M9)** — window the KG, detect emerging / fading /
  renamed / relation_shift events, summarize as markdown.
- **Main graph + supervisor (M10)** — `build_main_graph()` wires the 7
  subgraphs with a supervisor (intent classification), critic and replan
  loop; SQLite checkpointer; `interrupt_before=["graph_update"]` for
  human approval of KG writes (see ADR-0004).
- **CLI, demo, seed (M11)** — `ara` command (typer): `ingest`, `query`,
  `hypothesize`, `evolve`, `demo`; `scripts/demo.py` (3 papers → KG →
  hypotheses → experiment → evolution report → `artifacts/demo_report.md`,
  fully offline, exit 0); `scripts/seed_neo4j.py` (idempotent 30-triple
  biomedical seed).
- **Evaluation harness (M12)** — `ara/eval/`: set-based extraction F1 vs. a
  gold set of 21 manually verified triples from real PubMed papers
  (PMID:15829966, PMID:15829967; curation rules in `ara/eval/gold/README.md`),
  hypothesis grounding metric, `run_eval()`, `python -m ara.eval` rich table
  with threshold exit codes, regression tests, `make eval`, and a
  paths-gated eval CI workflow. Measured at release: **extraction_f1 =
  0.9333, grounding = 1.0000**.
- **Docs & release (M13)** — mkdocs-material site (this site) deployed to
  GitHub Pages via Actions, README rewrite with badges, `CHANGELOG.md`,
  4 ADRs, prompt catalog, `docs`/`docs-build` make targets, `LICENSE` (MIT).

### Changed

- `mypy --strict` is now green repo-wide (52 files, 0 errors) — all 49
  pre-existing strict-mode errors fixed in M12.
- Test suite: **61 passing** (was 59 at M11; +2 eval regression tests).
- README: quickstart, CLI, configuration, architecture Mermaid, evaluation
  output, badges and link to the docs site.

### Fixed

- Legacy tests broken at an earlier HEAD (imports of non-existent modules,
  syntax errors) — repaired; suite green since M11.
- Ruff/black formatting normalized repo-wide.

### Known limitations

- The LLM is mocked everywhere (deterministic extractor + static hypothesis
  generator); eval metrics score that deterministic pipeline, not a real LLM.
- Gold set is small (2 papers / 21 triples + 3 documented distractors).
- NetworkX `query_cypher` supports only a read-only `MATCH ... RETURN ...`
  subset; use the Neo4j backend for full Cypher.
- `ara evolve` snapshots the previous window to `<kg_store>.prev.json`; the
  first run after a fresh store reports everything as `emerging`.
