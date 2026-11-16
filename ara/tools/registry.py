"""Central registry of tool names used across the package."""

from typing import List


TOOLS: List[str] = [
    "pubmed",
    "arxiv",
    "pdf",
    "entity_linking",
    "vector",
    "neo4j",
    "networkx",
]


def get_tool(name: str):
    """
    Return the tool name if it is registered, otherwise raise ``ValueError.
    This is a placeholder – real tool implementations live in ``ara/clients.
    """
    if name in TOOLS:
        return name
    raise ValueError(f"Tool '{name}' is not registered")
