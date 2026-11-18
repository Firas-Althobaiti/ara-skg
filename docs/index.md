# ARA-SKG

**Autonomous Research Assistant for Scientific Knowledge Graphs.**

ARA-SKG is a LangGraph-based framework that ingests biomedical literature,
extracts entities and relations into a scientific knowledge graph (KG), answers
natural-language queries, generates provenance-grounded hypotheses, proposes
experiments, and tracks concept evolution over time — all behind a typed CLI
and a one-command offline demo.

It ships with a measurable quality layer (`make eval`: extraction F1 and
hypothesis grounding against a hand-verified gold set of real PubMed triples),
two interchangeable KG backends (offline NetworkX/JSON and Neo4j), and a fully
tested, `mypy --strict`-clean codebase.

[Get started in 5 minutes →](quickstart.md)

- 📖 Quickstart: [quickstart](quickstart.md)
- 🏗 Architecture & ADRs: [architecture](architecture.md)
- 🧪 Evaluation harness: run `make eval` (see the
  [README](https://github.com/Firas-Althobaiti/ara-skg#readme))
- 📦 Source code: [github.com/Firas-Althobaiti/ara-skg](https://github.com/Firas-Althobaiti/ara-skg)
