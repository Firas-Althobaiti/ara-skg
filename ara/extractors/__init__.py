"""Extraction strategies: mock (deterministic, default) vs live (LLM)."""

from __future__ import annotations

from typing import Literal

from ara.extractors.base import Extractor
from ara.extractors.llm import LLMExtractor
from ara.extractors.mock import MockExtractor

ExtractorMode = Literal["mock", "live"]


def get_extractor(mode: ExtractorMode = "mock") -> Extractor:
    """Factory: ``mock`` → deterministic parser (CI-safe), ``live`` → LLM."""
    if mode == "live":
        return LLMExtractor()
    return MockExtractor()


__all__ = ["Extractor", "ExtractorMode", "MockExtractor", "LLMExtractor", "get_extractor"]
