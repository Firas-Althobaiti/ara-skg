"""Simple entity‑linking client – maps names to canonical IDs/aliases."""

from __future__ import annotations

from ara.schemas.entity import EntityRef


class EntityLinkingClient:
    """Placeholder implementation – maps a few common aliases."""

    def __init__(self) -> None:
        # Example mapping: lower‑cased name → canonical name
        self.aliases = {
            "brca1": "geneA",
            "p53": "proteinX",
            "cancer": "diseaseB",
        }

    async def link_entity(self, name: str, entity_type: str) -> EntityRef:
        canonical = self.aliases.get(name.lower())
        if canonical:
            return EntityRef(name=canonical, type=entity_type, id=canonical)
        return EntityRef(name=name, type=entity_type, id=name)

    async def bulk_link(self, entities: list[EntityRef]) -> list[EntityRef]:
        return [await self.link_entity(e.name, e.type) for e in entities]
