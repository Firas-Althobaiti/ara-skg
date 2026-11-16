
**File: `docs/adr/0001-subgraphs-and-checkpointer.md`**
```markdown
# ADR 001 – Subgraphs and Checkpointing

## Status
Accepted

## Context
LangGraph provides a flexible directed‑acyclic graph of **nodes** (functions) and **edges** (transitions). To keep the system modular, maintainable, and resilient to failures, we split the overall research workflow into **small, focused subgraphs**. Each subgraph is a compiled `Graph` that can be executed independently, allowing:

- **Parallel execution** of independent steps (e.g., extraction can run while literature is being fetched).
- **Clear ownership** of state – each subgraph receives an `ARAState` and returns a partial update.
- **Built‑in barrier nodes** for synchronisation (e.g., waiting for extraction to finish before upserting).

## Decision
We adopt a **subgraph‑per‑concern** architecture:

| Concern | Subgraph name | Primary responsibilities |
|---------|---------------|--------------------------|
| Literature acquisition & chunking | `ingestion` | fetch → chunk → persist embeddings |
| Entity & relation extraction | `extraction` | LLM‑driven parsing, linking, validation |
| Knowledge‑graph mutation | `graph_update` | resolve IDs, ensure schema, atomic upserts |
| Natural‑language query | `query` | NL → Cypher → answer |
| Hypothesis generation | `hypothesis` | propose → ground → rank → critique |
| Experiment design | `experiment` | propose → validate |
| Concept evolution tracking | `evolution` | window → detect → summarize |

Each subgraph is compiled into a `Graph` object (`ara.graphs.<name>.build_<name>_graph`) and can be invoked from the **supervisor** node (`ara.nodes.supervisor`). The supervisor decides which subgraph to run based on the current `intent` field of `ARAState`.

## Constraints & Trade‑offs
- **State size**: `ARAState` grows as papers and triples accumulate. We mitigate this by **checkpointing** after each subgraph finishes (see below) and by using **lazy loading** for large subgraph results.
- **Interruptibility**: Write‑heavy operations (`upsert_kg`) are wrapped in a **barrier** that can be interrupted. If the user aborts, the partial transaction is rolled back, preserving graph consistency.
- **Parallelism**: LangGraph’s native parallel execution allows multiple subgraphs to run concurrently when their input state is already materialised (e.g., extraction can proceed while the ingestion subgraph is still fetching papers).

## Alternatives Considered
- **Monolithic pipeline**: A single long‑running node would simplify state handling but would make debugging and parallelism difficult.
- **Separate processes**: Using separate processes for each concern adds communication overhead and complicates state sharing.

## Implementation Notes
- **Checkpointing** is performed by the supervisor after each subgraph returns its partial state. The checkpoint format is a JSON‑serialisable dict saved to `checkpoints/<timestamp>.json`.
- **Interrupt handling** uses LangGraph’s `interrupt_before` barrier. The supervisor marks `upsert_kg` as the critical step; if the user sends an interrupt, the node raises a custom exception that the supervisor catches and rolls back any partially applied changes.
- **Testing**: Each subgraph has its own unit‑test suite (Phase 12) and integration tests that spin up a temporary Neo4j container.

## Rationale
Splitting the workflow into subgraphs aligns with the **single‑responsibility principle**, makes the system **easier to reason about**, and leverages LangGraph’s native support for **barriers**, **checkpointing**, and **parallel execution** — all essential for an autonomous, long‑running research assistant.

---

*Next ADR: 002 – LLM Factory and Structured Output*  
