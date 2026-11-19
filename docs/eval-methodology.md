# Evaluation methodology

How ARA-SKG measures itself — and what the numbers do and do not mean.

## The two modes

| | `make eval` (mock) | `make eval-live` (live) |
|---|---|---|
| Extractor | deterministic regex/keyword parser (`MockExtractor`) | real LLM (`LLMExtractor`, gpt-4o-mini) |
| When | CI on every push/PR — offline, free | **manual only** (`workflow_dispatch`), needs `OPENAI_API_KEY` |
| Cost | $0 | ~$0.01 per full run over the gold set |
| Gold | `gold/sample_triples.jsonl` (legacy, regression only) | `gold/real_abstracts.jsonl` (20 triples hand-verified from 4 real PubMed abstracts) + `gold/distractors.jsonl` (10 near-misses) |

`make eval` is a **regression gate, not a quality score**: the legacy gold was
curated from strings the mock itself parses, so its F1 = 0.9333 is circular —
it proves the parser didn't change, nothing more. That is why v1.1 added the
real-abstract gold and the live mode.

`make eval-live` measures **real LLM performance** against gold curated by a
human from real PubMed abstracts (raw abstracts committed under
`gold/raw_abstracts/`, so the gold is reproducible).

## Measured results (v1.1.0, 2026-11-19)

| mode | extraction_f1 | precision | recall | distractor_rejection | n_predicted | n_gold |
|---|---|---|---|---|---|---|
| mock (legacy gold) | 0.9333 | — | — | — | — | 21 |
| mock (real gold) | 0.000 | 0.0 | 0.0 | 1.0 | 0 | 20 |
| **live (real gold)** | **0.31** | 0.21 | 0.55–0.60 | **1.0** | ~52 | 20 |

The mock scores 0.0 on the real gold precisely because the real abstracts are
natural language, not the mock's `S - p - O` format — the two golds measure
different things (pinned by a test).

## How matching works

A predicted triple matches a gold triple iff:

- the **predicate matches exactly** after normalization (lowercase,
  punctuation stripped), and
- **both entity names match** — exact after normalization, or token Jaccard
  ≥ 0.5 with stopwords removed (so "inhibition of PARP" matches "PARP
  inhibition", "gamma-H2AX foci formation" matches "gamma-H2AX foci"), and
- **direction is preserved** — (subject, object) are ordered.

Because the predicate must match exactly and direction is ordered, the
distractor set (right entities + wrong predicate, or right predicate +
reversed direction) is a genuine precision guard: `distractor_rejection = 1.0`
means the extractor emitted **none** of the 10 near-miss triples.

## Why F1 = 0.31 is not a failure — and not a pass

The ship bar was F1 ≥ 0.6. Live F1 = 0.31, so the bar was **not met**, and we
report that plainly. But the number decomposes honestly:

- `distractor_rejection = 1.0` — the LLM does not confuse predicate or
  direction; it understands the extraction task.
- `recall ≈ 0.55–0.60` — it finds most stated relations.
- The F1 gap comes from **predicate canonicalization**: the gold curator
  normalized free text onto a controlled vocabulary ("are acutely sensitive
  to" → `sensitive_to`, "are important for" → `involved_in`, one sentence →
  two triples). The live extractor is constrained to a 20-term relation
  inventory via structured output, but the model still picks a different
  inventory term than the curator did, and exact predicate matching counts
  that as a miss.

## What v1.2 will add

1. **Predicate canonicalization** — map both gold and predicted predicates
   through one canonicalization layer (synonym groups / embeddings) before
   matching.
2. **LLM-judge matching** — for borderline entity/predicate pairs, a judge
   model scores semantic equivalence instead of string/Jaccard matching.
3. **Bigger gold set** — more abstracts, so F1 has statistical meaning beyond
   n=20.

## Reproduce

```bash
cp .env.example .env   # put a real OPENAI_API_KEY in .env
make eval              # mock regression (always works offline)
EVAL_CACHE=1 make eval-live   # live; caches LLM responses in artifacts/.llm_cache/
```

The report is written to `artifacts/eval_live_<date>.md` with both modes
side-by-side. CI never runs live mode; `.github/workflows/eval-live.yml`
triggers on `workflow_dispatch` only and needs the `OPENAI_API_KEY` repo
secret. A full live run costs ~$0.01 (gpt-4o-mini, ~7.5k tokens); the
`$0.50` cap is enforced by the small gold set + the optional file cache
(`EVAL_CACHE=1`).
