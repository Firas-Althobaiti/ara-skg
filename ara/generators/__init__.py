"""Hypothesis-generator strategies: mock (default) vs live (LLM)."""

from __future__ import annotations

from typing import Literal

from ara.generators.base import HypothesisGenerator
from ara.generators.llm import LLMGenerator
from ara.generators.mock import MockGenerator

GeneratorMode = Literal["mock", "live"]


def get_generator(mode: GeneratorMode = "mock") -> HypothesisGenerator:
    """Factory: ``mock`` → deterministic (CI-safe), ``live`` → LLM."""
    if mode == "live":
        return LLMGenerator()
    return MockGenerator()


__all__ = ["HypothesisGenerator", "GeneratorMode", "MockGenerator", "LLMGenerator", "get_generator"]
