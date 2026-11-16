"""Simple end‑to‑end demo that runs the ingestion → extraction → KG → query pipeline."""

import asyncio
from ara import get_settings, get_logger
from ara.tools import TOOLS
from ara.clients.kg_networkx import NetworkXKnowledgeGraphClient  # fallback client
from ara.nodes.ingestion import ingest_papers
from ara.nodes.extraction import extract_entities, extract_relations, link_entities, validate_triples
from ara.nodes.graph_update import resolve_triples, ensure_schema, upsert_kg
from ara.nodes.query import classify_query, nl2cypher, guard_cypher, run_cypher, synthesize_answer

async def run_pipeline():
    logger = get_logger()
    logger.info("Demo started")
    state = {}  # start with empty ARAState (will be populated by nodes)

    # 1️⃣ Ingestion
    state = await ingest_papers(state)

    # 2️⃣ Extraction
    state = await extract_entities(state)
    state = await extract_relations(state)
    state = await link_entities(state)
    state = await validate_triples(state)

    # 3️⃣ KG Update
    state = await resolve_triples(state)
    state = await ensure_schema(state)
    state = await upsert_kg(state)

    # 4️⃣ Query (example)
    state = await classify_query(state)
    state = await nl2cypher(state)
    state = await guard_cypher(state)
    state = await run_cypher(state)
    state = await synthesize_answer(state)

    logger.info("Demo pipeline completed")
    print("Pipeline finished.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
