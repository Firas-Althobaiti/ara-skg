"""Load a tiny 30-triple biomedical seed graph into Neo4j (idempotent).

Run with ``make seed`` / ``python scripts/seed_neo4j.py`` after
``docker compose up -d``.  Connection settings come from the environment
(``NEO4J_URI`` / ``NEO4J_USER`` / ``NEO4J_PASSWORD``, see ``.env.example``).

Idempotency: every triple is written with Cypher ``MERGE`` (see
:meth:`ara.clients.neo4j.Neo4jKnowledgeGraphClient.upsert_triples`), so
re-running the script reports ``added=0, updated=30`` and changes nothing.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

# Make the repo's own `ara` package importable when run as `python scripts/seed_neo4j.py`.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

from ara.clients.neo4j import Neo4jKnowledgeGraphClient  # noqa: E402
from ara.config import get_settings  # noqa: E402
from ara.logging import get_logger  # noqa: E402
from ara.schemas.entity import EntityRef  # noqa: E402
from ara.schemas.triple import Provenance, Triple  # noqa: E402

console = Console()
logger = get_logger("ara.seed")

# (subject, subject_type, predicate, object, object_type, confidence, paper_id)
SEED_SPEC: list[tuple[str, str, str, str, str, float, str]] = [
    ("BRCA1", "gene", "associated_with", "Breast cancer", "disease", 0.95, "PMID:9000001"),
    ("BRCA1", "gene", "encodes", "BRCA1 protein", "protein", 0.99, "PMID:9000002"),
    ("BRCA1 protein", "protein", "interacts_with", "RAD51", "protein", 0.90, "PMID:9000003"),
    ("RAD51", "protein", "involved_in", "DNA repair", "pathway", 0.93, "PMID:9000004"),
    ("TP53", "gene", "encodes", "p53 protein", "protein", 0.99, "PMID:9000005"),
    ("p53 protein", "protein", "regulates", "BAX", "gene", 0.88, "PMID:9000006"),
    ("p53 protein", "protein", "involved_in", "Apoptosis", "pathway", 0.91, "PMID:9000007"),
    ("TP53", "gene", "associated_with", "Lung cancer", "disease", 0.90, "PMID:9000008"),
    ("EGFR", "gene", "associated_with", "Lung cancer", "disease", 0.87, "PMID:9000009"),
    ("EGFR", "gene", "encodes", "EGFR protein", "protein", 0.98, "PMID:9000010"),
    ("EGFR protein", "protein", "activates", "MAPK signaling", "pathway", 0.89, "PMID:9000011"),
    ("KRAS", "gene", "encodes", "KRAS protein", "protein", 0.98, "PMID:9000012"),
    ("KRAS protein", "protein", "activates", "MAPK signaling", "pathway", 0.92, "PMID:9000013"),
    ("Imatinib", "drug", "inhibits", "ABL1", "protein", 0.94, "PMID:9000014"),
    (
        "ABL1",
        "protein",
        "associated_with",
        "Chronic myeloid leukemia",
        "disease",
        0.93,
        "PMID:9000015",
    ),
    ("Imatinib", "drug", "treats", "Chronic myeloid leukemia", "disease", 0.96, "PMID:9000016"),
    ("PARP1", "protein", "involved_in", "DNA repair", "pathway", 0.92, "PMID:9000017"),
    ("Olaparib", "drug", "inhibits", "PARP1", "protein", 0.95, "PMID:9000018"),
    ("Olaparib", "drug", "treats", "Breast cancer", "disease", 0.90, "PMID:9000019"),
    ("PARP1", "protein", "interacts_with", "BRCA1 protein", "protein", 0.85, "PMID:9000020"),
    ("Tamoxifen", "drug", "treats", "Breast cancer", "disease", 0.88, "PMID:9000021"),
    ("Tamoxifen", "drug", "binds", "ESR1", "protein", 0.91, "PMID:9000022"),
    ("ESR1", "protein", "associated_with", "Breast cancer", "disease", 0.84, "PMID:9000023"),
    ("PTEN", "gene", "regulates", "PI3K pathway", "pathway", 0.89, "PMID:9000024"),
    ("PI3K pathway", "pathway", "involved_in", "Cell cycle", "pathway", 0.86, "PMID:9000025"),
    ("MYC", "gene", "regulates", "Cell cycle", "pathway", 0.83, "PMID:9000026"),
    ("Cisplatin", "drug", "induces", "Apoptosis", "pathway", 0.90, "PMID:9000027"),
    ("Cisplatin", "drug", "treats", "Lung cancer", "disease", 0.82, "PMID:9000028"),
    ("CFTR", "gene", "associated_with", "Cystic fibrosis", "disease", 0.97, "PMID:9000029"),
    ("HBB", "gene", "associated_with", "Sickle cell disease", "disease", 0.96, "PMID:9000030"),
]


def build_seed_triples() -> list[Triple]:
    """Build the 30 :class:`Triple` seed objects from :data:`SEED_SPEC`."""
    triples: list[Triple] = []
    for subj, subj_type, pred, obj, obj_type, conf, pmid in SEED_SPEC:
        triples.append(
            Triple(
                subject=EntityRef(name=subj, type=subj_type, id=subj.lower().replace(" ", "_")),
                predicate=pred,
                object=EntityRef(name=obj, type=obj_type, id=obj.lower().replace(" ", "_")),
                confidence=conf,
                provenance=Provenance(
                    paper_id=pmid,
                    chunk_id="seed",
                    span=0,
                    extracted_by="seed_neo4j",
                ),
            )
        )
    return triples


async def seed(client: Any) -> dict:
    """Ensure schema and upsert the seed triples; returns the delta."""
    await client.ensure_schema()
    return await client.upsert_triples(build_seed_triples())


async def main() -> int:
    """Connect to Neo4j (settings from env) and load the seed graph."""
    settings = get_settings()
    logger.info("seeding neo4j", uri=settings.NEO4J_URI)
    triples = build_seed_triples()
    console.print(f"Seeding [bold]{len(triples)}[/bold] triples into {settings.NEO4J_URI} ...")
    async with await Neo4jKnowledgeGraphClient.create(
        uri=settings.NEO4J_URI, user=settings.NEO4J_USER, password=settings.NEO4J_PASSWORD
    ) as client:
        delta = await seed(client)
    table = Table(title="Seed triples", header_style="bold cyan")
    table.add_column("#", justify="right")
    table.add_column("Subject")
    table.add_column("Predicate")
    table.add_column("Object")
    table.add_column("Conf.", justify="right")
    table.add_column("Paper")
    for i, t in enumerate(triples, 1):
        table.add_row(
            str(i),
            t.subject.name,
            t.predicate,
            t.object.name,
            f"{t.confidence:.2f}",
            t.provenance.paper_id,
        )
    console.print(table)
    console.print(
        f"[bold green]Done.[/bold green] added={delta.get('added', 0)} updated={delta.get('updated', 0)} "
        "(idempotent: re-running reports added=0)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
