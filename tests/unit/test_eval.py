"""Regression thresholds for the Phase-12 evaluation metrics.

``run_eval()`` is executed once per module (it runs the offline extraction +
hypothesis pipeline over the gold papers) and both tests assert on its result.
"""

from __future__ import annotations

import pytest

from ara.eval import run_eval


@pytest.fixture(scope="module")
def metrics() -> dict[str, float]:
    return run_eval()


def test_run_eval_returns_both_metrics(metrics: dict[str, float]) -> None:
    assert set(metrics) == {"extraction_f1", "grounding"}
    assert metrics["extraction_f1"] >= 0.6  # regression threshold


def test_grounding_is_perfect(metrics: dict[str, float]) -> None:
    assert metrics["grounding"] == 1.0  # every hypothesis >= 2 provenance-linked triples
