"""Unit tests for the PubMed client (issue #12).

All HTTP is mocked with pytest-httpx — no live network calls.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from ara.clients.pubmed import PubMedClient, PubMedParseError

ESEARCH_JSON = {"esearchresult": {"idlist": ["111", "222"]}}

EFETCH_XML = b"""<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>111</PMID>
      <Article>
        <ArticleTitle>BRCA1 mutations in breast cancer</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">BRCA1 is a tumor suppressor.</AbstractText>
          <AbstractText Label="RESULTS">Germline mutations increase risk.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Smith</LastName><ForeName>Alice</ForeName></Author>
          <Author><LastName>Doe</LastName><Initials>J</Initials></Author>
        </AuthorList>
        <Journal><JournalIssue><PubDate><Year>2021</Year></PubDate></JournalIssue></Journal>
      </Article>
    </MedlineCitation>
    <PubmedData><ArticleIdList>
      <ArticleId IdType="pubmed">111</ArticleId>
      <ArticleId IdType="doi">10.1000/xyz</ArticleId>
    </ArticleIdList></PubmedData>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>222</PMID>
      <Article>
        <ArticleTitle>PARP inhibition in BRCA-mutated cancers</ArticleTitle>
        <Abstract><AbstractText>Olaparib extends survival.</AbstractText></Abstract>
        <AuthorList>
          <Author><LastName>Lee</LastName><ForeName>Bo</ForeName></Author>
        </AuthorList>
        <Journal><JournalIssue><PubDate><MedlineDate>2020 Fall</MedlineDate></PubDate></JournalIssue></Journal>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


@pytest.mark.asyncio
async def test_two_papers_with_real_abstracts(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=ESEARCH_JSON)
    httpx_mock.add_response(content=EFETCH_XML)
    client = PubMedClient(api_key="fake-key")  # fake string; never reads real .env
    papers = await client.search_pubmed("BRCA1 breast cancer")
    await client.close()

    assert len(papers) == 2
    p0 = papers[0]
    assert p0.id == "PMID:111"
    assert p0.abstract != "Placeholder abstract."
    assert "tumor suppressor" in p0.abstract and "increase risk" in p0.abstract
    assert p0.title == "BRCA1 mutations in breast cancer"
    assert p0.authors == ["Smith Alice", "Doe J"]
    assert p0.year == 2021
    assert p0.chunks == []
    assert papers[1].year == 2020  # MedlineDate fallback

    reqs = httpx_mock.get_requests()
    # exactly 2 requests: one esearch + ONE batched efetch (no N+1)
    assert len(reqs) == 2
    assert "esearch" in str(reqs[0].url) and "efetch" in str(reqs[1].url)
    assert "111" in str(reqs[1].url) and "222" in str(reqs[1].url)  # batch id list
    assert all("api_key=fake-key" in str(r.url) for r in reqs)  # via params, not concat


@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(json=ESEARCH_JSON)
    httpx_mock.add_response(content=EFETCH_XML)
    client = PubMedClient()
    papers = await client.search_pubmed("brca1")
    await client.close()

    assert len(papers) == 2
    esearch_calls = [r for r in httpx_mock.get_requests() if "esearch" in str(r.url)]
    assert len(esearch_calls) == 2  # 429 retried, then succeeded


@pytest.mark.asyncio
async def test_zero_results_raises_value_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"esearchresult": {"idlist": []}})
    client = PubMedClient()
    with pytest.raises(ValueError, match="No PubMed results for query: 'typo query'"):
        await client.search_pubmed("typo query")
    await client.close()


@pytest.mark.asyncio
async def test_malformed_xml_raises_domain_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=ESEARCH_JSON)
    httpx_mock.add_response(content=b"<PubmedArticleSet><oops")
    client = PubMedClient()
    with pytest.raises(PubMedParseError, match="malformed XML"):
        await client.search_pubmed("brca1")
    await client.close()
