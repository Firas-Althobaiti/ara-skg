"""Unit tests for the entity-linking client (issue #17).

Default behaviour must be a NO-OP: real names like "brca1"/"p53" are
returned unchanged. The fake alias map only applies when passed explicitly.
"""

from __future__ import annotations

import pytest

from ara.clients.entity_linking import EntityLinkingClient


@pytest.mark.asyncio
async def test_default_client_is_noop() -> None:
    linker = EntityLinkingClient()
    brca1 = await linker.link_entity("BRCA1", "gene")
    assert brca1.name == "BRCA1" and brca1.id == "brca1"  # slugified, not "geneA"
    p53 = await linker.link_entity("p53", "protein")
    assert p53.name == "p53" and p53.id == "p53"  # not "proteinX"


@pytest.mark.asyncio
async def test_explicit_alias_map_applies_only_to_listed_names() -> None:
    linker = EntityLinkingClient(alias_map={"brca1": "geneA"})
    assert (await linker.link_entity("brca1", "gene")).name == "geneA"
    assert (await linker.link_entity("p53", "protein")).name == "p53"  # unchanged


@pytest.mark.asyncio
async def test_empty_name_raises_value_error() -> None:
    linker = EntityLinkingClient()
    with pytest.raises(ValueError, match="entity name is required"):
        await linker.link_entity("", "gene")
    with pytest.raises(ValueError, match="entity name is required"):
        await linker.link_entity("   ", "gene")
