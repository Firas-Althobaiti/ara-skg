from ara.clients.arxiv import ArXivClient
from ara.clients.entity_linking import EntityLinkingClient
from ara.clients.neo4j import Neo4jKnowledgeGraphClient
from ara.clients.pdf import PDFClient
from ara.clients.pubmed import PubMedClient
from ara.clients.vector import VectorStoreClient


async def test_client_instantiation():
    # Neo4j client (no real connection needed for the test)
    async with Neo4jKnowledgeGraphClient.create(
        uri="bolt://localhost:7687", user="neo4j", password="***"
    ) as kg:
        assert kg is not None

    # Vector store client (no real DB needed for the test)
    vec = VectorStoreClient(persist_directory="./tmp_vector")
    await vec.add_paper  # will be a no‑op because paper not provided
    await vec.close()

    # PubMed client (no network calls in this test)
    pubmed = PubMedClient()
    await pubmed.close()

    # ArXiv client
    arxiv = ArXivClient()
    await arxiv.close()

    # PDF client
    pdf = PDFClient()
    await pdf.close()

    # Entity linking client
    linker = EntityLinkingClient()
    entity = await linker.link_entity("p53", "protein")
    assert entity.name == "proteinX"
