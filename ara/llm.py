"""LLM factory and structured‑output helper."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeVar, cast

from langchain_core.callbacks import BaseCallbackHandler
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ara.logging import get_logger

T = TypeVar("T", bound=BaseModel)


class _UsageLoggingCallback(BaseCallbackHandler):  # type: ignore[misc]
    """Log token usage for every LLM call so cost is visible."""

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        llm_output = getattr(response, "llm_output", None) or {}
        usage = llm_output.get("token_usage") if isinstance(llm_output, dict) else None
        if usage:
            get_logger("ara.llm").info(
                "llm call tokens",
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
            )


def get_llm(tier: Literal["reason", "fast"] = "reason") -> ChatOpenAI:
    """
    Return a LangChain ChatOpenAI instance.

    - ``reason → ``gpt-4o (full‑size model, low temperature)
    - ``fast   → ``gpt-4o-mini (smaller, faster model)

    Credentials come from Settings (which reads ``.env``), not only from
    ``os.environ`` — so a project-local ``.env`` is enough for live mode.
    """
    from ara.config import get_settings

    model_id = "gpt-4o-mini" if tier == "fast" else "gpt-4o"  # fast → mini, reason → full
    settings = get_settings()

    return ChatOpenAI(
        model=model_id,
        temperature=0,
        max_tokens=2000,
        max_retries=3,
        callbacks=[_UsageLoggingCallback()],
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


def structured(llm: ChatOpenAI, schema: type[T]) -> Callable[[BaseModel], T]:
    """
    Wrap a ChatOpenAI instance with structured output for the given Pydantic schema.

    The returned callable accepts a LangChain ``BaseMessage and returns an
    instance of ``schema.
    """
    return cast(Callable[[BaseModel], T], llm.with_structured_output(schema))
