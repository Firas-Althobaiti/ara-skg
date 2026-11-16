from langgraph import Graph
from ara.state import ARAState
from ara.nodes.ingestion import route_sources, fetch_papers, chunk_papers, persist_chunks, error

def build_ingestion_graph():
    g = Graph()
    # Dummy start and end nodes (required by LangGraph)
    g.add_node("START", lambda: None)
    g.add_node("END", lambda: None)

    # Actual processing nodes
    g.add_node("route_sources", route_sources)
    g.add_node("fetch_papers", fetch_papers)
    g.add_node("chunk_papers", chunk_papers)
    g.add_node("persist_chunks", persist_chunks)
    g.add_node("error", error)

    # Edges
    g.add_edge("START", "route_sources")
    g.add_conditional_edge("route_sources", lambda state: state.task and state.task != "", target="fetch_papers")
    g.add_edge("fetch_papers", "chunk_papers")
    g.add_edge("chunk_papers", "persist_chunks")
    g.add_conditional_edge("persist_chunks", lambda state: len(state.get("papers", [])) == 0, target="error")
    g.add_edge("error", "END")
    return g
