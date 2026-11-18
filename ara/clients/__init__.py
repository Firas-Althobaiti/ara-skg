"""Public API for client modules."""

from .arxiv import ArXivClient
from .entity_linking import EntityLinkingClient
from .kg import KGClient, KnowledgeGraphClient, get_kg_client
from .kg_networkx import NetworkXKnowledgeGraphClient
from .neo4j import Neo4jKnowledgeGraphClient
from .pdf import PDFClient
from .pubmed import PubMedClient
from .vector import VectorStoreClient

__all__ = [
    "KGClient",
    "KnowledgeGraphClient",
    "get_kg_client",
    "Neo4jKnowledgeGraphClient",
    "NetworkXKnowledgeGraphClient",
    "VectorStoreClient",
    "PubMedClient",
    "ArXivClient",
    "PDFClient",
    "EntityLinkingClient",
]
