# Gold set — `sample_triples.jsonl`

21 manually verified biomedical triples used as the answer key for the
extraction F1 metric (`ara/eval/extraction_f1.py`).

## Source papers (real, not synthetic)

| Paper ID | Citation |
|---|---|
| `PMID:15829966` | Bryant HE et al. "Specific killing of BRCA2-deficient tumours with inhibitors of poly(ADP-ribose) polymerase." *Nature* 2005;434(7035):913-7. doi:10.1038/nature03443 |
| `PMID:15829967` | Farmer H et al. "Targeting the DNA repair defect in BRCA mutant cells as a therapeutic strategy." *Nature* 2005;434(7035):917-21. doi:10.1038/nature03445 |

Abstracts were retrieved from PubMed (NCBI E-utilities, `efetch db=pubmed`)
and each gold triple was verified by hand against the abstract text: the
subject/predicate/object in every line is a statement the paper actually
makes (11 triples from PMID:15829966, 10 from PMID:15829967).

## Provenance rules

- One JSON object per line, shaped exactly like `Triple.model_dump()` so it
  can be loaded with `Triple.model_validate` / `coerce_triple`.
- `provenance.paper_id` is always the real PubMed ID (`PMID:...`);
  `extracted_by` is `"gold_curator"` (human), `confidence` is `1.0`.
- `subject.id` / `object.id` carry the HGNC gene ID where the entity is a
  gene with a stable identifier (BRCA1 `HGNC:1100`, BRCA2 `HGNC:1101`,
  PARP1 `HGNC:9234`); otherwise `null`. Metric matching uses **names**, not
  IDs, because the extractor emits `id == name`.
- Tokenization rule: hyphens in entity names are written as spaces
  (e.g. "single strand breaks", not "single-strand breaks") so the
  mock extractor's `-` segment delimiter parses each statement as exactly
  three segments. Matching normalizes case/whitespace, so this does not
  affect scoring.

## What is NOT in the gold set (deliberate distractors)

The evaluation papers (`eval_papers()` in `ara/eval/extraction_f1.py`) contain
a few extra parseable statements that the curator excluded from the gold set
because they are background, negative, or speculative rather than core
verified findings:

- "PARP1 knockout mice - free_of - early onset tumours" (negative result)
- "tumour specificity - results_from - BRCA2 loss" (background rationale)
- "DNA repair pathways - cooperate - to repair damage" (background)

These make precision < 1.0, so the F1 score is a real measurement and not a
trivial 1.0.

## Regeneration

Re-fetch the abstracts with:

```bash
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=15829966,15829967&rettype=abstract&retmode=text"
```
