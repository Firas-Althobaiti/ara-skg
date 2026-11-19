# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — coming in v1.1+

### Added
- Real LLM mode via strategy pattern: `ara/extractors/` (MockExtractor
  default, LLMExtractor via `get_llm("fast")` + structured output) and
  `ara/generators/` for hypotheses; `EXTRACTION_MODE` / `HYPOTHESIS_MODE`
  (`mock` default, CI-safe; `live` requires `OPENAI_API_KEY` and logs a
  cost warning) (#19). Live prompts in `ara/prompts/extraction_live.py` /
  `hypothesis_live.py` (legacy prompts untouched).
- Non-circular eval: `gold/real_abstracts.jsonl` (20 hand-verified triples
  from 4 real PubMed abstracts committed under `gold/raw_abstracts/`) +
  `gold/distractors.jsonl` (10 near-misses) with `eval_with_mode()`
  reporting precision/recall/F1 **and** `distractor_rejection`; legacy
  `sample_triples.jsonl` kept for regression (#19).
- `make eval-live` + `eval-live.yml` (workflow_dispatch ONLY, 10-min
  timeout, artifact upload) and `EVAL_CACHE=1` file cache
  (`ara/eval/_llm_cache.py`, gitignored) to keep live runs under $0.50 (#19).
- Token-usage logging on every LLM call (`ara/llm.py` callback) (#19).
- Eval matching is now lexical-but-meaningful: predicate exact (normalized),
  direction preserved, entity names fuzzy (token Jaccard ≥ 0.5 after
  stopword/punctuation normalization) — so surface variants match but
  wrong-predicate / reversed distractors are still rejected (#19 follow-up).
- `get_llm()` passes `OPENAI_API_KEY`/`OPENAI_BASE_URL` from Settings (reads
  `.env`), so live mode works with a project-local `.env` (#19 follow-up).
- Live extraction constrains the predicate to a standard biomedical relation
  inventory via a `Literal` on the structured-output schema (#19 follow-up).

### Fixed
- `test_settings_defaults` no longer fails when a real `.env` exists — it
  now runs from a clean cwd with all env vars deleted (#19).
- EntityLinkingClient is a no-op by default (names unchanged, id=slugified
  name); the old fake alias map (brca1→geneA, p53→proteinX) is dev-only via
  `LINKING_MODE=alias` + explicit `alias_map`, with a warning logged (#17).
- PDF ingestion: `parse_pdf(path, *, paper_id=...)` — paper_id is required
  (ValueError if empty), 50 MB size cap, unreadable/corrupt PDFs wrapped in
  `PDFParseError`, and every chunk now carries the paper_id derived from the
  file basename, so triple provenance and the grounding eval survive (#17).
- New e2e test actually exercises `interrupt_before=["graph_update"]`: the
  run halts before the subgraph (KG verified empty), resumes on the same
  thread, and writes the triples; a non-graph_update route does not halt (#17).
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
