"""LLM factory and structured‑output helper."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypeVar, cast

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def get_llm(tier: Literal["reason", "fast"] = "reason") -> ChatOpenAI:
    """
    Return a LangChain ChatOpenAI instance.

    - ``reason → ``gpt-4o (full‑size model, low temperature)
    - ``fast   → ``gpt-4o-mini (smaller, faster model)
    """
    model_id = "gpt-4o-mini" if tier == "fast" else "gpt-4o"  # fast → mini, reason → full

    return ChatOpenAI(
        model=model_id,
        temperature=0,
        max_tokens=2000,
        max_retries=3,
    )


def structured(llm: ChatOpenAI, schema: type[T]) -> Callable[[BaseModel], T]:
    """
    Wrap a ChatOpenAI instance with structured output for the given Pydantic schema.

    The returned callable accepts a LangChain ``BaseMessage and returns an
    instance of ``schema.
    """
    return cast(Callable[[BaseModel], T], llm.with_structured_output(schema))
