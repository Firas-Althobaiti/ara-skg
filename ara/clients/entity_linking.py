"""Entity-linking client.

The default is NO-OP: names are returned unchanged, with ``id`` set to a
slugified form of the name. Do not ship fake alias maps to production —
they corrupt real entity IDs (e.g. a real PubMed "BRCA1" mislabeled as
"geneA"). A dev-only alias map (:data:`DEV_ALIAS_MAP`) is available only by
passing ``alias_map`` explicitly — ``LINKING_MODE=alias`` wires it in
:func:`ara.nodes.extraction.link_entities_node` with a warning.
"""

from __future__ import annotations

import re

from ara.schemas.entity import EntityRef

DEV_ALIAS_MAP: dict[str, str] = {
    "brca1": "geneA",
    "p53": "proteinX",
    "cancer": "diseaseB",
}
"""Dev-only aliases. Never active by default."""


def slugify(name: str) -> str:
    """Lowercase slug: non-alphanumeric runs become ``_``."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or name.lower()


class EntityLinkingClient:
    """Maps entity names to canonical IDs.

    With no ``alias_map`` (the default) this is a no-op: the entity keeps
    its name and gets ``id=slugify(name)``.
    """

    def __init__(self, alias_map: dict[str, str] | None = None):
        self._aliases = alias_map or {}

    async def link_entity(self, name: str, entity_type: str) -> EntityRef:
        if not name or not name.strip():
            raise ValueError("entity name is required")
        canonical = self._aliases.get(name.lower())
        if canonical:
            return EntityRef(name=canonical, type=entity_type, id=canonical)
        return EntityRef(name=name, type=entity_type, id=slugify(name))

    async def bulk_link(self, entities: list[EntityRef]) -> list[EntityRef]:
        return [await self.link_entity(e.name, e.type) for e in entities]
