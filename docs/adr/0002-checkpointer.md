# ADR-0002 — SQLite checkpointer by default

- **Status:** Accepted (v1.0.0)
- **Date:** 2026-11-18

## Context

LangGraph needs a checkpointer to persist state between runs, support resume
after interrupts, and enable time-travel debugging. The main graph is compiled
at import time as a module-level singleton (`app = build_main_graph(...)`),
where no asyncio event loop exists yet.

## Decision

Use `langgraph.checkpoint.sqlite.SqliteSaver` over a local
`checkpoints.sqlite` file as the default checkpointer, constructed
synchronously (the sync `SqliteSaver`, not `AsyncSqliteSaver`, because the
singleton is built at import time outside any event loop). If the
`langgraph-checkpoint-sqlite` extra is not installed, fall back to
`MemorySaver`. Async code paths (e.g. the e2e tests) pass an
`AsyncSqliteSaver` explicitly via `build_main_graph(checkpointer=...)`.

## Consequences

- Runs survive process restarts; `thread_id`-keyed resume works after the
  `graph_update` interrupt (ADR-0004).
- Zero external services for the default (offline) experience — important for
  the demo and CI.
- The SQLite file is git-ignored (`checkpoints.sqlite`, `*.sqlite`).
- Trade-off: single-writer semantics of SQLite; fine for local/CLI use,
  not for concurrent multi-process servers.

## Alternatives

- **Postgres checkpointer** — better for concurrent servers; adds an external
  dependency; deferred to a hosted deployment.
- **In-memory only** — no persistence; would break resume-after-interrupt,
  which the human-approval flow depends on.
