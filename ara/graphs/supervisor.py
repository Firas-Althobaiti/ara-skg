"""Backwards-compatible re-export of the main graph builder.

The supervisor wiring lives in :mod:`ara.graphs.main`.
"""

from ara.graphs.main import SUBGRAPHS, app, build_main_graph

__all__ = ["build_main_graph", "app", "SUBGRAPHS"]
