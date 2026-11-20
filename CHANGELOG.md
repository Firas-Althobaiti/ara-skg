# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- LLM-judge matching in the live eval (#28): `ara/eval/judge.py`
  (`TripleJudge` — rule fast-path, cached structured-output judge with
  `JudgeVerdict{equivalent, confidence, reason}`); cache
  key = `judge|<PROMPT_VERSION>|<sha256 of normalized predicted>|<sha256 of
  normalized gold>` + model name, so prompt or model changes never reuse
  stale verdicts.
- `ara/prompts/judge.py` (NEW): `JUDGE_PROMPT` (v1) + `JudgeVerdict` schema.
- `ara/eval/extraction_f1.py`: new async `prf1_judged(predicted, gold, judge)`
  — same bipartite semantics as `prf1`, but rule-unmatched pairs go to the
  judge. `eval_with_mode` uses it only in live mode (`JUDGE_MODE=rule+llm`
  forced there; `rule` forced in mock). `distractor_rejection` is ALWAYS
  rule-based only — the judge never sees distractors.
- `ara/config.py`: `JUDGE_MODE: Literal["rule","rule+llm"] = "rule"`,
  `MAX_JUDGE_CALLS: int = 100`. Budget guard raises `BudgetExceededError`
  (never silently truncates); judge-call logging:
  `judge calls: N (rule-matched: M, llm-judged: K, llm-accepted: A)` in
  eval-live console output and the markdown report.

### Known Limitations (measured 2026-11-21, `EVAL_CACHE=1 make eval-live`)
- Live F1 unchanged at 0.3636 (target 0.5 not met): of 24×20 pred/gold pairs
  none had matching entities with a mismatched predicate, so the judge made
  0 calls. Remaining misses are entity-level (relation selection under the
  6-per-chunk cap), not predicate-equivalence. distractor_rejection stays
  1.0. See HANDOFF "Phase 15C — Live Eval Results"; v1.3B = reason-tier pass
  + bigger gold.

## [1.2.0] — 2026-11-19

### Added
- Predicate canonicalization: 20-verb inventory (`CANONICAL_PREDICATES`)
  with ~55 synonyms (`PREDICATE_SYNONYMS`); idempotent `canonicalize()`.
- LLM Literal-constrained schema: `RelationTriple.predicate` is a
  Literal over exactly the 20 canonical verbs; the prompt lists all 20
  and forbids free-form predicates.
- Over-prediction guard in `LLMExtractor._post_process`:
  confidence floor 0.6, top-6 by confidence per chunk, before/after
  logging.
- Optional LLM-fallback canonicalizer (`ara/canonicalizer.py`,
  `CANONICALIZER_MODE=rule` default; `rule+llm` opt-in with file cache).
- Bipartite non-consuming matching in `prf1` (a merged prediction
  counts for each gold it covers).
- Entity matching now requires ≥2-token containment to prevent
  "BRCA1" from matching "BRCA1 dysfunction".

### Changed
- Live F1: 0.3056 → 0.3636
- Live precision: 0.2115 → 0.3333
- Live recall: 0.5500 → 0.4000 (recall drop from the cap tradeoff)
- n_predicted per eval run: 52 → 24
- distractor_rejection: 1.0000 (unchanged, by design)

### Fixed
- LLM no longer emits non-canonical predicates
  ("is_associated_with_increased_risk_of" etc.) — the schema rejects
  them at the boundary.
- Eval no longer double-counts a merged prediction against multiple
  gold triples inconsistently.

### Known Limitations (v1.2.0)
- Live F1 = 0.3636, still below the 0.5 target.
- Root cause: under a 6-triple cap, gpt-4o-mini does not consistently
  select the curator's 6 relations when the abstract contains 10+.
- v1.3 will address: LLM-judge matching, larger gold set, optional
  gpt-4o reason-tier pass. See HANDOFF "Phase 15B — v1.2.0 Release".

## [1.1.0] — 2026-11-19

Phases 14A–14G. Headline: the pipeline is hardened and transactional, ingestion
fetches real papers, and the eval can measure a **real LLM** — with honest
numbers (live F1 = 0.31, below the 0.6 bar; see Known Limitations).

### Added
- Strategy-pattern extraction/hypothesis: `ara/extractors/` + `ara/generators/`
  (`mock` default, CI-safe; `live` via `get_llm(...)` + structured output),
  `EXTRACTION_MODE` / `HYPOTHESIS_MODE`, live prompts in
  `ara/prompts/extraction_live.py` / `hypothesis_live.py` (legacy prompts
  untouched), cost warning when live (#19, #20).
- Non-circular eval: `gold/real_abstracts.jsonl` (20 hand-verified triples from
  4 real PubMed abstracts, raw abstracts committed under `gold/raw_abstracts/`)
  + `gold/distractors.jsonl` (10 near-miss triples); `eval_with_mode()` reports
  precision/recall/F1 **and** `distractor_rejection`; legacy
  `sample_triples.jsonl` kept for regression (#19, #20).
- `make eval-live` + `.github/workflows/eval-live.yml` (**workflow_dispatch
  ONLY**, 10-min timeout, report artifact), `EVAL_CACHE=1` file cache
  (`ara/eval/_llm_cache.py`, gitignored, < $0.50/run cap), and per-call
  token-usage logging in `ara/llm.py` (#19).
- Eval matching is lexical-but-meaningful: predicate exact (normalized),
  direction preserved, entity names fuzzy (token Jaccard ≥ 0.5) — surface
  variants match, wrong-predicate/reversed distractors still rejected; live
  predicates constrained to a biomedical relation inventory via `Literal`;
  `get_llm()` reads `OPENAI_API_KEY`/`OPENAI_BASE_URL` from Settings (`.env`
  aware) (#21).
- Real PubMed/arXiv ingestion: one esearch + one batched `efetch` parsed with
  stdlib ElementTree (real titles, multi-section abstracts, authors, year,
  DOI); arXiv Atom feed with URL-encoded params and real summaries; both
  clients retry individual HTTP calls with tenacity backoff+jitter;
  `NCBI_API_KEY` support; zero-hit queries raise instead of silently
  returning empty (#12).
- Transactional KG writes on both backends: Neo4j upserts run as ONE
  transaction per batch (atomic), NetworkX writes via tmp+`os.replace`,
  `KGWriteError` + `rollback(delta)` on the client protocol (#11).
- PDF provenance enforcement: `parse_pdf(path, *, paper_id=...)` required,
  50 MB cap, `PDFParseError` on corrupt files, chunk paper_id derived from
  the filename; `EntityLinkingClient` is a no-op by default (`LINKING_MODE`,
  fake alias map dev-only with warning); e2e test that actually exercises
  `interrupt_before=["graph_update"]` halt/resume (#17).

### Fixed
- Unbounded replan loop crashing on persistent errors (bounded retries).
- PDF ingestion setting `paper_id=""`, breaking provenance and the grounding
  eval (#17).
- `EntityLinkingClient` hard-coded fake aliases (brca1→geneA, p53→proteinX)
  mislabeling real PubMed entities (#17).
- PubMed N+1 requests reading non-existent XML keys and storing
  `"Placeholder abstract."`; arXiv raw string interpolation breaking on
  spaces/`&` (#12).
- `test_settings_defaults` failing when a real `.env` exists (now runs from a
  clean cwd with env vars deleted) (#19).

### Known Limitations (v1.1)
- **Live eval F1 = 0.31 against the real-abstract gold — the 0.6 ship bar was
  NOT met.** `distractor_rejection = 1.0` shows the LLM understands the task;
  the F1 gap is a predicate-matching problem (no canonicalization layer yet).
  Tracked for v1.2. See `docs/eval-methodology.md`.
- NetworkX `query_cypher` remains a read-only `MATCH ... RETURN ...` subset;
  use the Neo4j backend for full Cypher.
- Neo4j read-only enforcement deferred to v1.2.

### Roadmap → v1.2
- Predicate canonicalization + LLM-judge matching in the eval (close the F1 gap)
- Full Cypher support on the NetworkX backend
- Real Neo4j end-to-end run in CI

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
