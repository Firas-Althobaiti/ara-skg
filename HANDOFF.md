# HANDOFF — ara-skg

## Phase 11 — Handoff

### (a) Public symbols exported

- `ara.cli` — typer app + console entry point `main()` (installed as `ara`):
  commands `ingest`, `query`, `hypothesize`, `evolve`, `demo`.
  Private helpers: `_use_kg_store`, `_get`, `_apply`, `_triple_rows`, `_hypothesis_table`.
- `ara.config.Settings` — new fields `ARA_KG_BACKEND` (`"networkx"` default | `"neo4j"`)
  and `ARA_KG_STORE` (default `"kg_store.json"`); new cached property `client` →
  `KnowledgeGraphClient` via `get_kg_client(self)`.
- `ara.clients.kg` — `KnowledgeGraphClient` (Protocol), alias `KGClient`,
  factory `get_kg_client(settings)`.
- `ara.clients.kg_networkx` — `NetworkXKnowledgeGraphClient` (JSON-persisted
  `networkx.DiGraph`; MERGE-semantics `upsert_triples`, `resolve_entity`,
  minimal read-only `query_cypher`, `subgraph`, `temporal_query`, `ensure_schema`,
  plus `all_triples()` / `stats()`), `KGDelta`, `_slug`.
- `ara.clients.neo4j` — `Neo4jKnowledgeGraphClient` (unchanged public surface; used by the seed script).
- `scripts/demo.py` — `DEFAULT_OUT`, `build_demo_graph()`, `run_demo(out_path, kg_store)`, `main()`.
- `scripts/seed_neo4j.py` — `SEED_SPEC` (30-triple biomedical seed), `build_seed_triples()`,
  `seed(client)`, `main()`.
- `pyproject.toml` — console script `ara = "ara.cli:main"`; deps added: `networkx`;
  dev dep added: `langgraph-checkpoint-sqlite` (needed by `build_main_graph` tests).
- Tests added: `tests/unit/test_cli.py`, `tests/e2e/test_demo.py` (CLI commands,
  demo report/KG artifacts, seed idempotency against the NetworkX client).

### (b) Known TODOs

- LLM is mocked everywhere (deterministic extractor + static hypothesis generator);
  wire `ara.llm.get_llm` / structured outputs into the nodes once an API key is available.
- `scripts/seed_neo4j.py` needs a live Neo4j (`make up`); idempotency is verified in
  tests against the NetworkX client, not against a real Neo4j in this environment.
- NetworkX `query_cypher` supports only `MATCH (n[:Label]) RETURN n.prop [AS x], ...`;
  full Cypher requires the Neo4j backend.
- `ara evolve` snapshots the previous window to `<kg_store>.prev.json`; the first run
  after a fresh store reports everything as `emerging` (verified), re-runs report none.
- Neo4j `subgraph()` tries APOC then falls back to a 1-hop pattern (APOC may be absent).
- `make type` (`mypy ara --strict`) is NOT green repo-wide: 65 pre-existing errors in
  18 modules (nodes/, graphs/, clients/vector|pubmed|pdf, schemas/state, …) that
  predate this phase. All files created/modified in this phase are strict-clean (0 errors).
- Legacy tests were broken at HEAD (imports of non-existent `ara.state`, syntax
  errors); fixed in this phase — suite is green: 59 passed.
- No `make` binary exists in this Windows container, so acceptance was verified via
  the exact recipe (`python scripts/demo.py`, exit 0) plus all five `ara` commands (exit 0).

### (c) Env vars added

- `ARA_KG_BACKEND` — `networkx` (default; offline JSON store, used by demo + CLI) | `neo4j`
- `ARA_KG_STORE` — JSON file path for the NetworkX backend (default `kg_store.json`;
  the demo uses `artifacts/demo_kg.json`). Both documented in `.env.example`.

## Phase 12 — Handoff

### (a) Public symbols exported

- `ara.eval` — `run_eval() -> dict[str, float]` (`{"extraction_f1": ..., "grounding": ...}`),
  re-exports: `GOLD_PATH`, `EVAL_PAPERS`, `eval_papers()`, `load_gold()`, `normalize()`,
  `triple_key()`, `extract_predicted()`, `prf1()`, `extraction_f1()`,
  `grounding_score()`, `is_grounded()`.
- `ara.eval.extraction_f1` — set-based precision/recall/F1 of the extraction pipeline
  vs. `ara/eval/gold/sample_triples.jsonl` (21 manually verified triples from real
  papers PMID:15829966 / PMID:15829967; curation rules in `ara/eval/gold/README.md`).
- `ara.eval.grounding` — fraction of hypotheses with >= 2 provenance-linked supporting triples.
- `ara.eval.__main__` — `python -m ara.eval` / `make eval`; prints a rich table,
  exits 1 when `extraction_f1 < 0.6` or `grounding < 1.0` (`THRESHOLDS`).
- `tests/unit/test_eval.py` — 2 regression tests (suite: 61 passing).
- `pyproject.toml` — new `[project.optional-dependencies] eval` group (pandas, tabulate).
- `.github/workflows/eval.yml` — `make eval` CI gated by a workflow-level `paths:`
  filter (`ara/nodes/**`, `ara/eval/**`, `scripts/**`, `tests/**`, `Makefile`,
  `pyproject.toml`). Note: GitHub has no job-level `paths:` filter; putting `paths:`
  on `ci.yml`'s `pull_request` trigger would have suppressed its lint/test jobs on
  unrelated PRs, so the eval job lives in its own workflow.
- Also in this phase: fixed all 49 pre-existing `mypy --strict` errors (type
  annotations, `dict[str, Any]`/`tuple[...]` parameterization, `cast` for
  TypedDict updates) — `make type` is now green repo-wide (52 files).

### (b) Known TODOs

- Metrics currently score the deterministic mocked-LLM pipeline, not a real LLM;
  re-run `make eval` once `OPENAI_API_KEY` is configured and the nodes use
  `ara.llm.get_llm` — thresholds (F1 >= 0.6, grounding == 1.0) will need
  re-baselining against real extraction output.
- Gold set is small (2 papers / 21 triples + 3 documented distractors); grow it
  before trusting F1 as a release gate. Distractors keep precision at 21/24,
  so measured F1 = 0.9333.
- The `eval` extras (pandas, tabulate) are declared for downstream analysis but
  the runtime table uses `rich` (already a core dep).
- No `make` binary exists in this Windows container; all `make` targets were
  verified by running their exact recipes (`python -m ara.eval`, `pytest`, ...).

### (c) Env vars added

- None. The eval harness is fully offline (mocked LLM, no KG backend needed);
  it reuses the existing `ARA_KG_*` settings only indirectly.
