from langgraph.graph import END, START, StateGraph

from ara.nodes.ingestion import (
    chunk_papers,
    error,
    fetch_papers,
    persist_chunks,
    route_sources,
)
from ara.state import ARAState


def build_ingestion_graph() -> StateGraph:
    """Build and compile the ingestion subgraph.

    Flow:
        START → route_sources → fetch_papers
                                    ├── (no papers) → error → END
                                    └── (papers)    → chunk_papers
                                                       → persist_chunks → END
    """
    g = StateGraph(ARAState)

    # 1. Register nodes
    g.add_node("route_sources", route_sources)
    g.add_node("fetch_papers", fetch_papers)
    g.add_node("chunk_papers", chunk_papers)
    g.add_node("persist_chunks", persist_chunks)
    g.add_node("error", error)

    # 2. Entry edge
    g.add_edge(START, "route_sources")
    g.add_edge("route_sources", "fetch_papers")

    # 3. Conditional: did we actually fetch any papers?
    g.add_conditional_edges(
        "fetch_papers",
        lambda state: "error" if not state.get("papers") else "chunk_papers",
        {
            "error": "error",
            "chunk_papers": "chunk_papers",
        },
    )

    # 4. Happy path
    g.add_edge("chunk_papers", "persist_chunks")
    g.add_edge("persist_chunks", END)

    # 5. Error path
    g.add_edge("error", END)

    return g.compile()
