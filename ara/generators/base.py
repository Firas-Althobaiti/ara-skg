"""Hypothesis generator protocol."""

from __future__ import annotations

from typing import Protocol

from ara.schemas import Hypothesis, Triple


class HypothesisGenerator(Protocol):
    """Strategy interface for hypothesis generation from KG triples."""

    async def generate(self, triples: list[Triple], n: int = 3) -> list[Hypothesis]:
        """Propose up to *n* hypotheses grounded in *triples*."""
        ...
