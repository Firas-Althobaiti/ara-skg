import asyncio
from ara.clients.kg_neo4j import Neo4jKnowledgeGraphClient
from ara.schemas.triple import Triple
from ara.schemas.entity import EntityRef


async def main():
    client = Neo4jKnowledgeGraphClient(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="",
    )
    # Ensure schema exists
    await client.ensure_schema()
    # Create a tiny seed graph
    seed_triples = [
        Triple(
            subject=EntityRef(name="GeneA", id="geneA"),
            predicate="expresses",
            object=EntityRef(name="ProteinX", id="proteinX"),
            confidence=0.95,
            provenance={
                "paper_id": "PMID:00000001",
                "chunk_id": "c1",
                "span": 0,
                "extracted_by": "seed",
            },
        ),
        Triple(
            subject=EntityRef(name="ProteinX", id="proteinX"),
            predicate="phosphorylates",
            object=EntityRef(name="KinaseY", id="kinaseY"),
            confidence=0.9,
            provenance={
                "paper_id": "PMID:00000002",
                "chunk_id": "c2",
                "span": 0,
                "extracted_by": "seed",
            },
        ),
    ]
    await client.upsert_triples(seed_triples)
    print("Seed graph loaded into Neo4j.")


if __name__ == "__main__":
    asyncio.run(main())
