"""Unit tests for the arXiv client (issue #12).

All HTTP is mocked with pytest-httpx — no live network calls.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from ara.clients.arxiv import ArXivClient

ATOM_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v2</id>
    <title>CRISPR   Cas9
    genome editing</title>
    <summary>  We show that CRISPR-Cas9   edits genomes. </summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Doe</name></author>
    <published>2023-01-05T00:00:00Z</published>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00002</id>
    <title>Base editing review</title>
    <summary>Base editors enable precise changes.</summary>
    <author><name>Carol Ray</name></author>
    <published>2023-03-11T00:00:00Z</published>
  </entry>
</feed>
"""


@pytest.mark.asyncio
async def test_query_with_spaces_is_url_encoded_and_summaries_real(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(content=ATOM_XML)
    client = ArXivClient()
    papers = await client.search_arxiv("crispr cas9", max_results=2)
    await client.close()

    url = str(httpx_mock.get_requests()[0].url)
    assert "crispr+cas9" in url or "crispr%20cas9" in url

    assert len(papers) == 2
    p0 = papers[0]
    assert p0.abstract != "Placeholder abstract."
    assert p0.abstract == "We show that CRISPR-Cas9 edits genomes."  # whitespace-normalized
    assert p0.title == "CRISPR Cas9 genome editing"
    assert p0.id == "http://arxiv.org/abs/2301.00001"  # /v2 stripped
    assert papers[1].id == "http://arxiv.org/abs/2301.00002"  # no version suffix
    assert p0.authors == ["Alice Smith", "Bob Doe"]
    assert p0.year == 2023
    assert p0.chunks == []


@pytest.mark.asyncio
async def test_ampersand_in_query_does_not_break_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(content=ATOM_XML)
    client = ArXivClient()
    await client.search_arxiv("crispr & cas9")
    await client.close()

    url = str(httpx_mock.get_requests()[0].url)
    assert "%26" in url  # raw & is encoded, cannot break param parsing
    assert "search_query=" in url
