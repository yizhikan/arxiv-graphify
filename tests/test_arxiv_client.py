"""Tests for arXiv API client."""
import pytest
import requests
from arxiv_graphify.arxiv_client import ArxivClient, parse_arxiv_response


@pytest.fixture
def client():
    """Create an arXiv client."""
    return ArxivClient()


def test_search_papers_integration(client):
    """Integration test for arXiv search."""
    try:
        results = client.search(category="cs.AI", max_results=3)
    except (requests.exceptions.ReadTimeout, requests.exceptions.HTTPError) as e:
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
            pytest.skip("arXiv API rate limited")
        elif isinstance(e, requests.exceptions.ReadTimeout):
            pytest.skip("arXiv API timeout")
        raise

    assert isinstance(results, list)
    assert len(results) <= 3
    for paper in results:
        assert "title" in paper
        assert "abstract" in paper
        assert "arxiv_id" in paper
        assert "published" in paper


def test_search_with_category(client):
    """Test search with specific category."""
    try:
        results = client.search(category="cs.LG", max_results=2)
    except (requests.exceptions.ReadTimeout, requests.exceptions.HTTPError) as e:
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
            pytest.skip("arXiv API rate limited")
        elif isinstance(e, requests.exceptions.ReadTimeout):
            pytest.skip("arXiv API timeout")
        raise

    assert isinstance(results, list)
    assert len(results) <= 2


def test_parse_arxiv_response():
    """Test XML response parsing."""
    xml_sample = """<?xml version='1.0'?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2012.12104v1</id>
        <title>Test Title</title>
        <summary>Test Abstract</summary>
        <published>2020-12-09T05:08:41Z</published>
        <category term="cs.AI"/>
        <author>
          <name>Test Author</name>
        </author>
        <link href="http://arxiv.org/pdf/2012.12104" title="pdf" type="application/pdf"/>
      </entry>
    </feed>"""
    results = parse_arxiv_response(xml_sample)
    assert len(results) == 1
    assert results[0]["arxiv_id"] == "2012.12104v1"
    assert results[0]["title"] == "Test Title"
    assert results[0]["abstract"] == "Test Abstract"
    assert results[0]["published"] == "2020-12-09"
    assert "cs.AI" in results[0]["categories"]
    assert "Test Author" in results[0]["authors"]
    assert results[0]["pdf_url"] == "http://arxiv.org/pdf/2012.12104"
