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
