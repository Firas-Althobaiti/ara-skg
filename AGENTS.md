# Agent Contract
- Python 3.11+, uv/pip, ruff + black + mypy strict.
- All public functions fully typed; Pydantic v2 for schemas.
- Every LangGraph node: `async def node(state: ARAState) -> dict` returning a partial state update.
- No prints — use `ara.logging.get_logger()`.
- Secrets only via `ara.config.Settings` (pydantic-settings, .env).
- Tests: pytest + pytest-asyncio; ≥80% coverage on `ara/schemas`, `ara/clients`, `ara/nodes`.
- Conventional Commits. One PR per phase.
- Do not invent files outside the layout in README.md.
