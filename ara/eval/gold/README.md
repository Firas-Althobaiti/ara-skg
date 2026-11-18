# Gold Set — Evaluation Reference

This directory contains manually-curated triples extracted from real
biomedical papers (PubMed). They serve as the "gold standard" for
measuring the extraction F1 score.

## Curation rules
- Each triple must be directly supported by the paper's abstract.
- Only relations with confidence >= 0.85 are included.
- Entities are normalized to lowercase IDs (e.g., "brca1", "breast_cancer").
- Provenance includes the PubMed ID and a span index.

## Coverage
- 6 real papers (PubMed IDs in provenance)
- 20 triples total
- Entity types: gene, protein, drug, disease, pathway
- Predicates: treats, inhibits, activates, encodes, associated_with, involved_in, targets, regulates