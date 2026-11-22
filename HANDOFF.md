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

## Phase 14F — Real LLM Mode

### (a) Public symbols exported

- `ara.extractors`: `Extractor` protocol, `MockExtractor`, `LLMExtractor`,
  `get_extractor(mode)` factory. `ara.generators`: `HypothesisGenerator`
  protocol, `MockGenerator`, `LLMGenerator`, `get_generator(mode)`.
- `ara.prompts.extraction_live` / `hypothesis_live`: live prompts +
  structured-output schemas (legacy `prompts/extraction.py` untouched).
- `Settings.EXTRACTION_MODE` / `HYPOTHESIS_MODE` (`mock` default |
  `live`), `Settings.EVAL_CACHE` (bool).
- `ara.eval.extraction_f1.eval_with_mode(mode, gold_path=REAL_GOLD_PATH)`,
  `load_raw_abstracts()`, `distractor_rejection_rate()`;
  `run_eval(mode="mock")` backward compatible.
- `ara.eval._llm_cache`: `cache_enabled/get/set` (EVAL_CACHE=1,
  `artifacts/.llm_cache/`, gitignored, keyed by sha256(prompt+model)).
- `ara.llm._UsageLoggingCallback` — logs token usage per LLM call.

### (b) What changed and why

- Extraction/hypothesis nodes now go through the strategy factories;
  live mode logs a one-liner that LLM calls incur cost. Mock behavior is
  byte-identical (logic moved verbatim; `_call_llm` kept as a compat shim).
- Eval circularity fixed: new gold `real_abstracts.jsonl` (20 triples
  hand-verified from 4 real PubMed abstracts fetched with the 14C client;
  raw abstracts committed under `gold/raw_abstracts/`, 5.1KB total) +
  `distractors.jsonl` (10 near-miss triples) → `eval_with_mode` reports
  f1 AND distractor_rejection. Legacy `sample_triples.jsonl` kept for
  regression (mock f1 there = 0.9333, provably circular — mock parses its
  own "S - p - O" format; on real abstracts mock f1 = 0.0, see test).
- `make eval-live` / `eval-live.yml` (workflow_dispatch ONLY, 10-min
  timeout, uploads `artifacts/eval_live_*.md`); CI push/PR paths unchanged.
- test_config: runs from a clean cwd with all env vars deleted → passes
  with AND without a real `.env`.

### (c) Tests

- `test_extractors.py` (mock == legacy output; factory; LLMExtractor with
  fake LLM stub), `test_generators.py` (same pattern), `test_eval_real.py`
  (gold files exist/sized <100KB; eval_with_mode shape; rejection <= 1.0;
  real-gold f1 != circular-gold f1).
- 100 tests pass (89 + 11 new), incl. test_config WITH `.env` present.
- ruff/black clean; mypy --strict 0 errors in 64 files; make eval PASS
  (F1 0.9333, grounding 1.0).

### (d) Env vars added

- `EXTRACTION_MODE`, `HYPOTHESIS_MODE` (`mock`|`live`), `EVAL_CACHE` (`1`).

### (e) Live eval results

- See "Phase 14F — Live Eval Results" below (manual `make eval-live`).

## Phase 14F — Live Eval Results

Manual `make eval-live` (EVAL_CACHE=1) against the 4 real PubMed abstracts,
gpt-4o-mini, 2026-11-19. Three prompt iterations; best/stable configuration
(controlled predicate inventory enforced as a `Literal` on the structured
schema + fuzzy entity matching in the eval):

| mode | f1 | precision | recall | distractor_rejection | n_predicted | n_gold |
|---|---|---|---|---|---|---|
| mock | 0.000 | 0.000 | 0.000 | 1.000 | 0 | 20 |
| live | 0.306–0.333 | 0.21–0.23 | 0.55–0.60 | 1.000 | 52 | 20 |

- Cost: ~7.5k tokens / ~$0.01 per full live run (well under the $0.50 cap);
  per-call token usage is logged by `_UsageLoggingCallback`.
- distractor_rejection = 1.0 in both modes: the matcher keeps the predicate
  exact and direction ordered, so near-miss triples are never matched.
- Honest read: live F1 ~0.3 is below the 0.6 "ship" bar. The residual gap is
  gold granularity — the gold curator split/normalized triples (e.g. one
  sentence "induce gamma-H2AX and RAD51 foci" → two gold triples
  "induce gamma-H2AX foci" + "induce RAD51 foci"; "are important for" →
  involved_in). Entity matching is fuzzy (token Jaccard ≥ 0.5) but predicate
  must match exactly, so copular/voice variants the model maps differently
  still miss. Raising F1 further means a canonicalization layer or an
  LLM-judge matcher — noted as future work, not silently loosened here.
- Report artifact: `artifacts/eval_live_20261119.md`; `eval-live.yml`
  workflow_dispatch verified manually once.

## Phase 14G — v1.1.0 Release

### (a) What shipped across 14A–14F
- Transactional KG writes on both backends (single-tx Neo4j, atomic tmp+replace
  NetworkX, `KGWriteError`/`rollback`) (#11)
- Real PubMed/arXiv ingestion: batched efetch, real abstracts, tenacity
  retries, `NCBI_API_KEY`, zero-hit errors (#12)
- PDF provenance enforcement (required `paper_id`, 50MB cap, `PDFParseError`),
  entity-linking no-op default (`LINKING_MODE`), real e2e
  `interrupt_before=["graph_update"]` halt/resume test (#17)
- Real LLM mode via strategy pattern (`EXTRACTION_MODE`/`HYPOTHESIS_MODE`,
  mock default / live opt-in) + non-circular eval (real-abstract gold 20
  triples + 10 distractors, `distractor_rejection`) + `make eval-live` /
  `eval-live.yml` (workflow_dispatch only) + `EVAL_CACHE` + token logging (#19–#21)

### (b) The honest F1 story
- Mock regression (CI): F1 = 0.9333, grounding = 1.0 — legacy gold, circular by
  construction, kept only as a regression gate.
- Live (manual, gpt-4o-mini, real-abstract gold): **F1 = 0.31, precision 0.21,
  recall 0.55–0.60, distractor_rejection = 1.0, ~$0.01/run**. The 0.6 ship bar
  was NOT met and is stated as such in README, CHANGELOG Known Limitations, and
  docs/eval-methodology.md. Root cause: predicate canonicalization missing —
  exact-predicate matching counts curator normalizations ("are important for"
  → `involved_in`) as misses even when the LLM's semantics are right.

### (c) Release artifacts
- `README.md` "Evaluation" section: mock vs live table, plain statement of 0.31
- `docs/eval-methodology.md` (new, linked from README + mkdocs nav): what each
  mode measures, matching rules, why 0.31 ≠ failure, reproduce steps
- `CHANGELOG.md` `[1.1.0]` with Added / Fixed / Known Limitations / Roadmap v1.2
- Tag `v1.1.0` + GitHub release on main

### (d) v1.2 roadmap
1. Predicate canonicalization + LLM-judge matching in the eval (close the F1 gap)
2. Full Cypher on NetworkX + Neo4j read-only enforcement + Neo4j e2e in CI
3. Grow the gold set beyond 4 papers / 20 triples

## Phase 15A — Predicate Canonicalization + Precision (#24)

### (a) What changed
- `ara/schemas/predicates.py` (NEW): `CANONICAL_PREDICATES` (20 verbs),
  `PREDICATE_SYNONYMS` (~55 entries), idempotent `canonicalize()`, and
  `predicate_group()` (coarse polarity classes for eval matching:
  positive_effect = {causes, activates, interacts_with, treats},
  negative_effect = {inhibits}).
- Live extraction schema is a `Literal` over the 20 canonical verbs (runtime
  assert keeps it in sync with `CANONICAL_PREDICATES`); prompt lists all 20
  verbatim + the verbatim "Only emit predicates from this list…" and
  "Do NOT emit more than 6 triples per abstract…" instructions + mapping hints.
- `LLMExtractor._post_process`: confidence floor 0.6, top-`MAX_RELATIONS_PER_CHUNK`
  (config, default 6) by confidence, before/after log. `CANONICALIZER_MODE`
  (`rule` default, zero LLM cost; `rule+llm` optional cached fallback in
  `ara/canonicalizer.py`, cache key includes model).
- Pipeline + eval canonicalize predicates on both sides
  (`ara/nodes/extraction.py`, `triple_match`); `prf1` is now bipartite
  (non-consuming); `entity_match` = exact | Jaccard ≥ 0.5 | 2+-token
  containment (single-token containment excluded so "BRCA1" ≠ "BRCA1 dysfunction").

### (b) BEFORE/AFTER (live eval, gpt-4o-mini, real-abstract gold, 2026-11-19)

| metric | v1.1.0 | v1.2A (this PR) |
|---|---|---|
| F1 | 0.3056 | **0.3636** |
| precision | 0.2115 | 0.3333 |
| recall | 0.5500 | 0.4000 |
| distractor_rejection | 1.0000 | 1.0000 |
| n_predicted | 52 | 24 |

### (c) Honest read — target F1 ≥ 0.5 NOT met
- Over-prediction fixed (52 → 24 predicted, ≤ 30 target ✓), distractor
  rejection stays 1.0 ✓, mock regression unchanged (0.9333/1.0) ✓.
- F1 0.31 → 0.36. Remaining gap is model behavior, not matching:
  lowest-confidence accepted predictions this run included generic statements
  ("targeted inhibition of particular DNA repair pathways treats cancer",
  conf 0.80) while gold triples like "PARP1 facilitates DNA repair",
  "PARP inhibitors induce gamma-H2AX foci", "BRCA1 mutations predispose_to
  breast cancer" were missed — the cap (6/abstract) forces choosing, and
  gpt-4o-mini does not consistently pick the curator's triples.
- Next (v1.2B): LLM-judge matching for entity/predicate equivalence + a
  "reason"-tier extraction pass on misses; or grow gold so F1 is less noisy.

### (d) Tests
- +17 tests (119 total): `test_predicates.py` (7), `test_extraction_precision.py`
  (3: cap ≤ 6, conf floor 0.6, prompt contains inventory + verbatim instructions),
  `tests/integration/test_eval_canonicalization.py` (5), `test_canonicalizer_llm.py` (4).
- ruff/black clean; mypy --strict 0 errors in 66 files; make eval PASS.

## Phase 15B — v1.2.0 Release (2026-11-19)

### Shipped in v1.2.0 (all from Phase 15A, PR #25)
- Predicate canonicalization (20 verbs + 55 synonyms, idempotent).
- LLM Literal-constrained schema — no free-form predicates.
- Over-prediction guard (confidence 0.6, top-6 by confidence).
- Optional LLM-fallback canonicalizer (rule default, rule+llm opt-in).
- Bipartite non-consuming matching in eval.
- Entity match: ≥2-token containment required.

### Honest metrics (measured on main, reproducible)
| metric               | v1.1.0 | v1.2.0 | Δ       |
|----------------------|--------|--------|---------|
| live F1              | 0.3056 | 0.3636 | +19%    |
| live precision       | 0.2115 | 0.3333 | +58%    |
| live recall          | 0.5500 | 0.4000 | −27%    |
| distractor_rejection | 1.0000 | 1.0000 | unchanged |
| n_predicted          | 52     | 24     | −54%    |

### Why we shipped at 0.36 rather than continue
- The cap-vs-curator gap is a model-choice problem, not a prompt one.
- Raising the cap to 10 was tested and lost F1 (precision fell faster
  than recall recovered).
- Ship v1.2.0 (precision win is real and useful), then v1.3 (LLM-judge)
  with room to iterate without blocking a release.

### v1.3 roadmap (priority order)
1. LLM-judge matching — expected F1 0.36 → 0.50–0.60.
2. Bigger gold set (50–100 triples) — reduces n=20 noise.
3. gpt-4o reason-tier option — better relation selection under cap.
4. Neo4j read-only enforcement — deferred from v1.1.

### v1.2.0 artifacts
- Tag: v1.2.0 on main
- Release notes: CHANGELOG excerpt
- Baseline file: artifacts/BASELINE_v1.1.md
- Live eval report: artifacts/eval_live_20261119.md (updated to v1.2.0)

## Phase 15C — LLM-Judge Matching (#28)

### What changed
- `ara/eval/judge.py` (NEW): `TripleJudge.equivalent(predicted, gold)` —
  rule-based `triple_match` fast path first (zero LLM cost), entity-mismatch
  pairs rejected without an LLM call (the judge's own rules reject those),
  otherwise a structured-output LLM judge (`JudgeVerdict{equivalent,
  confidence, reason}`, fast tier gpt-4o-mini). Verdicts cached in-memory
  per run and on disk via `ara/eval/_llm_cache.py` when `EVAL_CACHE=1`; cache
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

### Verification (offline, this PR)
- ruff/black clean; mypy --strict 0 errors in 68 files; **128 tests pass**
  (119 existing + 6 `tests/unit/test_judge.py` + 3
  `tests/integration/test_eval_with_judge.py`).
- `make eval` (mock) UNCHANGED: extraction_f1 0.9333, grounding 1.0, PASS.
- Mock live-shape check: `eval_with_mode("mock")` on real abstracts →
  distractor_rejection 1.0, judge stats all zero (rule-only, no LLM).

### Live eval results — MEASURED 2026-11-21 (EVAL_CACHE=1 make eval-live, gpt-4o-mini)
Report: `artifacts/eval_live_20261120.md`. Extraction calls were EVAL_CACHE
hits from the 2026-11-19 run, so predictions are identical to v1.2.0 (n=24).

| metric               | v1.2.0 | v1.3A (judge) | target  |
|----------------------|--------|---------------|---------|
| live F1              | 0.3636 | **0.3636**    | >= 0.5  |
| live precision       | 0.3333 | 0.3333        | >= 0.45 |
| live recall          | 0.4000 | 0.4000        | >= 0.55 |
| distractor_rejection | 1.0000 | **1.0000**    | = 1.0   |
| n_predicted          | 24     | 24            | —       |
| judge calls          | N/A    | **0** (max 100) | <= 100 |
| incremental cost     | —      | $0 (cache hits + 0 judge calls) | <= $0.02 |

**Target NOT met — and the judge had nothing to judge.** Of 24×20 pred/gold
pairs: 8 rule-matched, **0** had matching entities with a mismatched
predicate, and the remaining pairs all differ in entities (which the judge's
own rules reject). The LLM judge therefore made zero calls and F1 is
unchanged. The 12 unrecalled gold triples are entity-level misses, not
predicate-equivalence misses, e.g. gold "PARP inhibition | causes | apoptosis"
vs emitted "inhibition of PARP | causes | persistence of DNA lesions"
(subject matches, object doesn't), gold "BRCA1 mutations | predispose_to |
breast cancer" vs emitted "mutations in BRCA1 and BRCA2 | associated_with |
breast and other cancers". Full lists: unmatched preds are mostly generic
("PARP inhibitors | part_of | combination strategies", conf 0.9) — the
6-per-chunk cap again forced model-level choices, confirming the v1.2.0
finding that this is a model-choice problem, not a matching problem.

### Implication for v1.3B
- LLM-judge matching is shipped and safe (0 calls, DR 1.0, budget intact) but
  does not move F1 on this gold — it will matter once entities align better.
- The F1 lever is relation *selection* under the cap, not matching: gpt-4o
  reason-tier pass on missed gold (roadmap item 3) and/or a bigger gold set
  (item 2). Relaxing the judge's entity rule (subset/superset acceptance)
  was considered and rejected — it would erode distractor_rejection.

## Phase 15D — gpt-4o Diagnostic + v1.3.0 Release (#31)

### One-shot gpt-4o diagnostic (2026-11-22, no cache, repo defaults untouched)
- Method: scratch driver monkeypatched `get_llm` → gpt-4o for BOTH
  extraction and judge; `EVAL_CACHE` unset. 9 LLM calls (8 extraction +
  1 judge), 7,041 prompt + 1,986 completion tokens ≈ **$0.04** (budget $0.20).
- Result: **F1 0.3636, P 0.3333, R 0.4000, DR 1.0, n_pred 24 — identical to
  the gpt-4o-mini v1.2.0 baseline.** Judge fired once (accepted:
  "treats" ≡ "kill" for drug effect on tumors) but the accepted pair
  connected an already-recalled gold to an already-precise prediction, so
  F1 did not move.
- Gate F1 ≥ 0.45 NOT met → no reason-mode feature PR. gpt-4o picks the same
  shape of relations at ~10× cost; reason-tier extraction pass is NOT
  recommended on this evidence.
- Artifact: `artifacts/gpt4o_diagnostic_20261122.md` (gitignored).

### v1.3.0 release (docs-only PR)
- Ships v1.3A (LLM-judge matching, PR #29) with honest metrics: live F1
  0.3636 on both models, distractor_rejection 1.0, mock 0.9333/1.0.
- CHANGELOG `[1.3.0]` with Added + Known Limitations (incl. the gpt-4o
  diagnostic); README eval table gains the v1.3.0 row; roadmap → v1.4
  (bigger gold set, Neo4j read-only; reason-tier dropped on evidence).

## Phase 15E — Judge Cache Fix + Explain Mode (#33)

### Fixes
- `TripleJudge.equivalent` now resolves the LLM model (`_resolved_model()`)
  BEFORE computing the cache key — the first call is no longer cached under
  `model="unknown"`. Regression test: `test_cache_key_uses_resolved_model`.
- New `python -m ara.eval --live --explain`: prints every missed gold triple
  and every unmatched prediction with the best candidate on the other side
  (entity Jaccard, even below the 0.5 threshold). Pure rule-based — no LLM
  calls. Implementation: `explain_mismatches()` in `ara/eval/extraction_f1.py`,
  `--explain` flag in `ara/eval/__main__.py`.

### Verification
- ruff/black clean; mypy --strict 0 errors in 68 files; **132 tests pass**
  (128 + 1 cache-key + 3 explain).
- `make eval` unchanged: 0.9333 / 1.0 PASS.
- `EVAL_CACHE=1 python -m ara.eval --live --explain` run 2026-11-22: F1 0.3636,
  judge 0 calls (cache hits), exit 0.

### Explain output (v1.3.0 gold, top 5 missed gold / top 5 unmatched predictions)
Missed gold:
1. `PARP1 | facilitates | DNA repair` — best: 'PARP1 | binds | DNA breaks' (J 0.33)
2. `PARP1 | attracts | DNA repair proteins` — best: 'PARP1 | binds | DNA breaks' (J 0.25)
3. `single-strand breaks | collapse | replication forks` — best J 0.00
4. `PARP inhibitors | kill | BRCA2-deficient tumours` — best: 'PARP inhibition | inhibits | tumours' (J 0.33)
5. `BRCA1 mutations | predispose_to | breast cancer` — best: 'mutations in BRCA1 and BRCA2 | associated_with | breast and other cancers' (J 0.25)

Unmatched predictions:
1. `PARP1 | activates | homologous recombination` — best gold J 0.00
2. `PARP inhibition | inhibits | tumours` — best: 'PARP inhibitors | kill | BRCA2-deficient tumours' (J 0.33)
3. `mutations in BRCA1 and BRCA2 | associated_with | breast and other cancers` — best: 'BRCA1 mutations | predispose_to | breast cancer' (J 0.25)
4. `inhibition of PARP | causes | persistence of DNA lesions` — best J 0.00
5. `PARP | inhibits | DNA damage response genes.` — best J 0.00

Read: near-misses cluster at J 0.25–0.33 (entity surface variants like
"PARP inhibition" vs "PARP inhibitors"), and most misses are generic/off-gold
statements at J 0.00. Input for v1.4B (gold-set growth): add abstracts whose
relations the extractor DOES hit, and decide whether J≈0.3 entity variants
should ever match (currently no — protects distractor_rejection).
