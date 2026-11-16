## Architecture (Mermaid)

```mermaid
flowchart TD
    subgraph Ingestion
        I[Ingestion Subgraph] -->|fetch| P[PubMed / arXiv / PDF]
        I -->|chunk| V[Vector Store]
    end
    subgraph Extraction
        E[Extraction Subgraph] -->|entities| N[Entities]
        E -->|relations| T[Triples]
        E -->|critic| C[Validate]
    end
    subgraph KG Update
        U[Graph Update Subgraph] -->|upsert| KG[Neo4j KG]
    end
    subgraph Query
        Q[Query Subgraph] -->|nl2cypher| Cypher[Cypher Engine]
        Q -->|synthesize| A[Answer]
    end
    subgraph Hypothesis
        H[Hypothesis Subgraph] -->|generate| Hyp[Hypotheses]
        H -->|rank| R[Ranking]
        H -->|critic| G[Grounding]
    end
    subgraph Experiment
        X[Experiment Subgraph] -->|propose| Exp[Experiments]
    end
    subgraph Evolution
        L[Evolution Subgraph] -->|window| Ev[Evolution Events]
    end
    I --> E --> U --> Q --> H --> X --> L --> A
