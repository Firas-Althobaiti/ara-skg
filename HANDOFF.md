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

## Phase 13 — Handoff (v1.0.0)

### (a) Final public API surface

- `ara.cli:main` — `ara` command: `ingest`, `query`, `hypothesize`, `evolve`, `demo`.
- `ara.graphs.main` — `build_main_graph(checkpointer=None)`, `app`, `SUBGRAPHS`
  (7 subgraphs); `interrupt_before=["graph_update"]`.
- `ara.graphs.<phase>` — `build_*_graph()` for ingestion, extraction,
  graph_update, query, hypothesis, experiment, evolution.
- `ara.nodes.*` — node functions per subgraph (see `ara/nodes/`).
- `ara.schemas` — `ARAState` (TypedDict) + `Paper`, `Entity`, `Triple`, `Hypothesis`, …
- `ara.clients.kg` — `KnowledgeGraphClient` protocol + `get_kg_client(settings)`;
  `kg_networkx.NetworkXKnowledgeGraphClient` (default, offline JSON);
  `neo4j.Neo4jKnowledgeGraphClient`; `pubmed` / `arxiv` / `pdf` / `vector` clients.
- `ara.config.Settings` — env-driven settings incl. `ARA_KG_BACKEND`, `ARA_KG_STORE`.
- `ara.llm.get_llm` — LLM factory (currently mocked by default; see TODOs).
- `ara.prompts.*` — 12 prompt constants, tagged v1.0.0 (see `docs/prompts.md`).
- `ara.eval` — `run_eval() -> {"extraction_f1", "grounding"}`; `python -m ara.eval`.
- `scripts/demo.py`, `scripts/seed_neo4j.py`.
- Package version: `1.0.0` (`pyproject.toml` + `ara/_version.py`); MIT `LICENSE`.

### (b) Shipped vs deferred

- Shipped: mkdocs-material site (Home/Quickstart/Architecture/4 ADRs/Prompts/
  Changelog stub), `CHANGELOG.md` (keep-a-changelog, M0–M13), README rewrite
  (badges, docs link, What's inside, Install, Quickstart, Evaluation, Roadmap),
  `docs.yml` (strict build gate on PRs touching docs) and `deploy-docs.yml`
  (GitHub Pages via Actions, `push` to `main` + `workflow_dispatch`),
  `docs`/`docs-build` make targets, `[docs]` extra, v1.0.0 tag + GitHub Release.
- Deferred to v1.1+: real-LLM wiring + eval re-baselining, larger gold set,
  `Send` fan-out, full Cypher on NetworkX, Neo4j in CI (see CHANGELOG Unreleased).

### (c) Site URL and deployment mechanism

- Site: https://firas-althobaiti.github.io/ara-skg/ (Pages source = GitHub
  Actions, already configured on the repo).
- Deploy: `.github/workflows/deploy-docs.yml` runs `mkdocs build --strict` on
  push to `main` (paths: `docs/**`, `mkdocs.yml`, `README.md`, `CHANGELOG.md`)
  and publishes `./site` via `actions/upload-pages-artifact@v3` +
  `actions/deploy-pages@v4` to the `github-pages` environment.
- `site/` is build output and stays git-ignored (`/site` in `.gitignore`).

### (d) Env vars added

- None.

## Phase 14A — Replan + Baseline

### (a) Public symbols exported

- `ara.nodes.supervisor.MAX_REPLANS` (= 3) — cap on replan cycles.
- `ara.schemas.ARAState` — new fields `replan_count: int` and `prev_baseline: bool`.
- `ara.nodes.evolution` — new `BASELINE_MARKER` (`"__baseline__"`),
  `BASELINE_MESSAGE`, `load_prev_snapshot(path) -> (triples, is_baseline_run)`,
  `save_snapshot(path, triples, *, baseline)` (atomic tmp+rename write).
- `ara.cli` — `ara evolve --reset-baseline` deletes the `.prev.json` snapshot.

### (b) What changed and why

- **Bounded replan loop** (was: unbounded `critic → replan → supervisor` cycle
  ending in `GraphRecursionError`): `replan_node` now increments
  `replan_count` and preserves `errors`; `critic_node` only requests a replan
  while `replan_count < MAX_REPLANS`, then routes to END with errors intact.
  Tests: `tests/unit/test_replan_loop.py` (persistent failure → END,
  `replan_count == 3`, 4 error messages preserved; success path → 0 replans).
- **Evolution baseline mode** (was: first run reported every existing triple
  as "emerging"): first `ara evolve` with no `.prev.json` writes
  `{"__baseline__": true, "triples": [...]}` and reports 0 events +
  "Baseline established…"; the next run diffs against that baseline normally.
  Tests: node-level (0 events on baseline run; exactly 2 events after +2
  triples; snapshot roundtrip) + CLI-level (first/second/`--reset-baseline`
  runs in `tests/unit/test_cli.py`).

### (c) Known TODOs

- Replan retries the *same* task/subgraph; a smarter replan would alter the
  plan (e.g. fall back to the mock source). Deferred.
- Baseline is per-KG-store (`.prev.json` next to the store); Neo4j-backed
  evolution snapshots are not yet persisted. Deferred.

### (d) Env vars added

- None.

## Phase 14B — Transactional KG

### (a) Public symbols exported

- `ara.clients.kg.KGWriteError` — raised by `upsert_triples` on batch
  failure; guarantees zero partial writes persisted.
- `ara.clients.kg.KGDelta` — moved to the protocol module (still importable
  from `ara.clients.neo4j` / `ara.clients.kg_networkx` for backwards compat).
- `KnowledgeGraphClient.rollback(delta)` — new protocol method. Neo4j:
  no-op (single transaction already rolled back). NetworkX: restores the
  pre-batch snapshot.
- `NetworkXKnowledgeGraphClient._apply_triple / _snapshot_touched /
  _restore_snapshot` — per-triple apply + snapshot/restore internals.

### (b) What changed and why

- **Neo4j**: `upsert_triples` now sends the whole batch as ONE `UNWIND`
  query inside `session.execute_write` (single transaction; any row
  failure rolls back everything). Per-row `was_present` flags come back in
  the same query, so the added/updated delta needs no post-commit DB call.
  Failures re-raised as `KGWriteError`. (Was: one `session.run` per triple,
  each auto-committed → partial writes on mid-batch failure.)
- **NetworkX**: `upsert_triples` snapshots the touched nodes/edges before
  mutating; on failure restores them and raises `KGWriteError`; `_save()`
  runs ONCE per successful batch and is now atomic (tmp + `os.replace`,
  same pattern as the evolution snapshot writer). Removed the per-entity
  `_save()` in `resolve_entity` (was O(n) disk writes per batch).
- **Node**: `rollback_on_error` now calls `client.rollback(delta)` before
  clearing `kg_delta` (was: cleared memory only — a no-op against the DB).
- KGDelta shape unchanged (`added`/`updated`/`edges`).

### (c) Tests

- `tests/integration/test_kg_transactional.py` (parametrized
  networkx + neo4j-via-fake-driver-with-real-tx-semantics): 3rd-of-4
  failure → `KGWriteError`, `subgraph(...) == []`, no partial file/store;
  clean retry persists all 4, re-run idempotent.
- `tests/unit/test_graph_update_node.py`: mid-batch failure → errors
  populated, `kg_delta` cleared, backend empty; success path persists and
  a later rollback call does not undo committed writes.

### (d) Env vars added

- None.

## Phase 14C — Real Literature Fetch

### (a) Public symbols exported

- `ara.clients._retry.RETRY` — typed tenacity decorator (HTTPStatusError /
  TransportError, exponential backoff + jitter, 4 attempts, reraise).
- `ara.clients.pubmed.PubMedClient(api_key=...)` / `PubMedParseError`;
  internals `_esearch` (one request), `_efetch` (ONE batched
  `rettype=abstract&retmode=xml`), `_parse_article` (stdlib ElementTree).
- `ara.clients.arxiv.ArXivClient` / `ArXivParseError`; `_get_feed` via httpx
  `params=`; Atom parsing strips `vN` id suffixes, whitespace-normalizes
  title/summary.
- `Settings.NCBI_API_KEY` — sent as `api_key` param (never string concat).

### (b) What changed and why

- PubMed: N+1 esummary loop (non-existent `article-title` key,
  `"Placeholder abstract."` chunks) replaced by esearch + single batched
  efetch XML; real abstract (multi-`<AbstractText>` joined), authors
  (LastName + ForeName/Initials), year (PubDate Year/MedlineDate), DOI
  located. `Paper.chunks = []` — chunking stays downstream in chunk_papers.
  0 hits → `ValueError(f"No PubMed results for query: {query!r}")`.
- arXiv: f-string URL replaced by httpx `params=` (spaces/`&` encoded);
  real `<summary>` abstracts; version suffix stripped from ids.
- Both: `@RETRY` on the single HTTP call only (not the pipeline);
  `raise_for_status()` before parsing so 429/5xx are retried.
- Malformed XML wrapped in domain errors (`PubMedParseError` /
  `ArXivParseError`), ET internals not leaked.

### (c) Tests

- `tests/unit/test_pubmed_client.py` (pytest-httpx, all mocked): 2-paper
  efetch with real abstracts + exactly 2 requests (no N+1) + api_key in
  params; 429→200 retry (esearch called twice); 0 ids → ValueError with
  query; malformed XML → PubMedParseError.
- `tests/unit/test_arxiv_client.py`: "crispr cas9" encoded (`+`/`%20`),
  "crispr & cas9" → `%26`; 2-entry Atom → real summaries, normalized
  title, `v2` suffix stripped, authors, year.
- 79 tests total (73 + 6 new). NOTE: local runs in this repo pick up the
  user's `.env` (contains OPENAI_API_KEY), which makes the pre-existing
  `test_settings_defaults` fail locally; verified green with a clean cwd —
  CI (no .env) is unaffected.

### (d) Env vars added

- `NCBI_API_KEY` (optional; raises NCBI limit 3 → 10 req/s).

### (e) Manual verification

Live smoke tests on merged main (2026-11-19, real NCBI/arXiv calls,
`NCBI_API_KEY` picked up from `.env`):

```
$ ara ingest "BRCA1 breast cancer" --source pubmed --kg-store <tmp>/smoke_kg.json
… Ingested papers (source=pubmed): PMID:43045764 (2026), PMID:43044269 (2026),
  PMID:43042434 (2026) — each with a real multi-section abstract (957–2111 chars,
  never "Placeholder abstract.") … KG delta: added=12 updated=0 — Ingest complete.

$ ara ingest "crispr cas9" --source arxiv --kg-store <tmp>/smoke_kg2.json
… Ingested papers (source=arxiv): http://arxiv.org/abs/2103.10667 (2021),
  http://arxiv.org/abs/2401.05714 (2024), … — real <summary> abstracts …

Direct client checks:
PubMedClient.search_pubmed("BRCA1 breast cancer", retmax=3) → 3 papers, real abstracts.
ArXivClient.search_arxiv("crispr cas9", max_results=2) → 2 papers, real summaries,
  ids version-stripped (…/2103.10667, not …/2103.10667vN).
```

Two real bugs were caught by these smoke tests and fixed in follow-up PRs:
#14 arXiv `http://` URL 301-redirects to https (httpx doesn't follow) → https URL;
#15 CLI passed the whole task string as the query → prefix stripped.

## Phase 14D — PDF, Linking, Interrupt

### (a) Public symbols exported

- `ara.clients.entity_linking.EntityLinkingClient(alias_map=None)` — no-op
  by default; `link_entity` raises `ValueError` on empty names; new
  `slugify()` helper; `DEV_ALIAS_MAP` (dev-only).
- `Settings.LINKING_MODE: Literal["noop", "alias"]` — "alias" wires
  DEV_ALIAS_MAP in `link_entities_node` with a structlog warning.
- `ara.clients.pdf.PDFClient.parse_pdf(path, *, paper_id)` — keyword-only
  required paper_id; `MAX_PDF_BYTES` (50 MB); `PDFParseError(message, path)`.

### (b) What changed and why

- Entity linking no longer corrupts real PubMed entities: default returns
  `EntityRef(name=name, type=type, id=slugify(name))`; fake aliases only via
  explicit `alias_map` / `LINKING_MODE=alias` (warns, dev-only).
- PDF: `paper_id=""` chunks broke provenance/grounding — now required
  (ValueError), derived from the file basename in `fetch_papers`; size cap
  with the byte count in the error; `fitz.open`/`get_text` wrapped so
  corrupt/encrypted PDFs raise `PDFParseError`, not bare exceptions.
  Text extraction logic unchanged.
- e2e: `interrupt_before=["graph_update"]` was never exercised — new real
  LangGraph halt/resume test.

### (c) Tests

- `tests/unit/test_entity_linking.py`: default no-op (brca1/p53 unchanged),
  explicit alias_map applies only to listed names, empty name → ValueError.
- `tests/unit/test_pdf_client.py`: empty paper_id → ValueError; oversized
  (cap monkeypatched down) → ValueError with size; corrupt bytes →
  PDFParseError; valid fitz-generated PDF → all chunks carry paper_id.
- `tests/e2e/test_main_graph_interrupt.py`: real run halts at
  `next == ("graph_update",)` with KG empty, resumes on same thread, KG has
  the triple, `next == ()`; a non-graph_update route ends without halting.
- 89 tests total (80 + 9 new). Same local `.env` caveat as 14C for
  test_settings_defaults (green from clean cwd; CI unaffected).

### (d) Env vars added

- `LINKING_MODE` (`noop` default | `alias` dev-only).
