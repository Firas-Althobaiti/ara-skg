# Quickstart — 5 minutes

Everything below runs **fully offline**: the demo uses the NetworkX KG backend
and a deterministic mocked LLM, so no API key and no Neo4j are required.

## 1. Clone & install

Requires **Python 3.11+** (developed and CI-tested on 3.11–3.13).

```bash
git clone https://github.com/Firas-Althobaiti/ara-skg.git
cd ara-skg
pip install -e .[dev]     # or: make install
```

## 2. Run the end-to-end demo

```bash
make demo                 # == python scripts/demo.py
```

In one command the demo:

```text
3 mock papers → extract entities/relations → validate → upsert into the KG
    → generate 3 hypotheses → ground → rank → critique
    → propose 1 experiment → validate feasibility
    → evolution diff (current window vs. previous) → report
```

It prints rich tables to the console and writes:

- `artifacts/demo_report.md` — the full markdown report
- `artifacts/demo_kg.json` — the persisted knowledge graph

Exit code is 0 on success.

## 3. Inspect the report

```bash
cat artifacts/demo_report.md     # papers, triples, hypotheses, experiment, evolution
```

## 4. Run the evaluation harness

```bash
make eval                 # == python -m ara.eval
```

Expected output:

```text
          ARA-SKG evaluation metrics
┌───────────────┬────────┬───────────┬────────┐
│ Metric        │  Value │ Threshold │ Status │
├───────────────┼────────┼───────────┼────────┤
│ extraction_f1 │ 0.9333 │    >= 0.6 │ PASS   │
│ grounding     │ 1.0000 │    >= 1.0 │ PASS   │
└───────────────┴────────┴───────────┴────────┘
```

`extraction_f1` is set-based F1 of the extraction pipeline against a
gold set of 21 manually verified triples from two real PubMed papers;
`grounding` is the fraction of hypotheses with ≥ 2 provenance-linked
supporting triples. The command exits 1 if a threshold is missed.

## 5. Use the CLI

```bash
ara demo                                        # same as make demo
ara ingest "demo biomedical corpus"             # fetch → extract → upsert
ara query "Which entities are in the KG?"       # guarded NL→Cypher + answer
ara hypothesize                                 # generate + ground + rank
ara evolve all                                  # KG window diff
```

Optional — real Neo4j backend with a seeded 30-triple KG:

```bash
make up        # docker compose up -d
make seed      # python scripts/seed_neo4j.py (idempotent)
```

## Next steps

- [Architecture](architecture.md) — the main graph, the 7 subgraphs, and the ADRs
- [Prompts](prompts.md) — every prompt shipped in `ara/prompts/`
- Development: `make lint` / `make type` / `make test` / `make cov`
- Docs site locally: `pip install -e .[docs]` then `make docs` (mkdocs serve)
