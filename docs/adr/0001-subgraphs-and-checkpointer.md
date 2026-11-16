# File: docs/adr/0001-subgraphs-and-checkpointer.md
# ADR‑0001 – Subgraphs, Checkpointer, Interrupts, Send Fan‑out

## Status
Accepted

## Context
The ARA‑SKG agent must perform many distinct tasks (ingest, extract, update KG, query, hypothesise, propose experiments, track evolution). A single monolithic graph would be hard to maintain and test.

## Decision
- **Subgraph per concern** – each subgraph is a compiled `Graph` that can be unit‑tested independently and reused.
- **Supervisor node** – a lightweight `classify_intent_node` routes the current task to the correct subgraph based on keywords in the task string.
- **Checkpointer (SQLite)** – the main graph is compiled with `SqliteSaver("checkpoints.sqlite")`, so the whole `ARAState` is persisted after every step. This allows resuming after a crash or a human interrupt.
- **Interrupts** – `interrupt_before=["graph_update"]` pauses execution before any write to the knowledge graph, enabling human approval.
- **Send fan‑out** – used inside the extraction subgraph to process each chunk in parallel (documented in the extraction graph).

## Consequences
+ Modular, testable code.
+ Easy to add new subgraphs.
+ State is durable across sessions.
- Slightly more complex wiring (supervisor + critic).
- Checkpointer adds I/O overhead (acceptable for research workloads).

```python


