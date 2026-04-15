"""arXiv API v2 client for paper search and metadata retrieval."""
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional


# arXiv namespace mappings
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArxivClient:
    """Client for arXiv API v2."""

    def __init__(
        self,
        api_base: str = "https://export.arxiv.org/api/query",
        timeout: int = 30,
    ):
        self.api_base = api_base
        self.timeout = timeout

    def search(
        self,
        category: str,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100,
        start: int = 0,
    ) -> List[Dict]:
        """
        Search arXiv papers.

        Args:
            category: arXiv category (e.g., "cs.AI", "cs.LG")
            keyword: Optional keyword to search in title/abstract
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_results: Maximum number of results to return
            start: Offset for pagination

        Returns:
            List of paper dicts with metadata
        """
        # Build search query
        query_parts = [f"cat:{category}"]
        if keyword:
            query_parts.append(f"all:{keyword}")

        search_query = " AND ".join(query_parts)

        # Build URL parameters
        params = {
            "search_query": search_query,
            "start": start,
            "max_results": min(max_results, 500),  # arXiv limit
        }

        # Make request
        response = requests.get(
            self.api_base,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()

        return parse_arxiv_response(response.text)

    def search_by_keywords(
        self,
        keywords: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results_per_keyword: int = 100,
    ) -> List[Dict]:
        """
        Search papers by multiple keywords.

        Args:
            keywords: List of arXiv keywords/categories
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_results_per_keyword: Max results per keyword

        Returns:
            List of unique paper dicts
        """
        all_papers = {}

        for keyword in keywords:
            # Check if it's a category (contains dot) or a keyword
            if "." in keyword:
                papers = self.search(
                    category=keyword,
                    max_results=max_results_per_keyword,
                )
            else:
                papers = self.search(
                    category="cs.AI",  # Default category
                    keyword=keyword,
                    max_results=max_results_per_keyword,
                )

            # Deduplicate by arxiv_id
            for paper in papers:
                all_papers[paper["arxiv_id"]] = paper

        return list(all_papers.values())


def parse_arxiv_response(xml_text: str) -> List[Dict]:
    """
    Parse arXiv API XML response.

    Args:
        xml_text: XML response from arXiv API

    Returns:
        List of paper dicts
    """
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall("atom:entry", NAMESPACES):
        paper = {}

        # Extract ID (remove http://arxiv.org/abs/ prefix)
        id_elem = entry.find("atom:id", NAMESPACES)
        if id_elem is not None and id_elem.text:
            paper["arxiv_id"] = id_elem.text.split("/abs/")[-1]

        # Extract title
        title_elem = entry.find("atom:title", NAMESPACES)
        if title_elem is not None and title_elem.text:
            paper["title"] = title_elem.text.strip()

        # Extract abstract/summary
        summary_elem = entry.find("atom:summary", NAMESPACES)
        if summary_elem is not None and summary_elem.text:
            paper["abstract"] = summary_elem.text.strip()

        # Extract published date
        published_elem = entry.find("atom:published", NAMESPACES)
        if published_elem is not None and published_elem.text:
            paper["published"] = published_elem.text[:10]  # YYYY-MM-DD

        # Extract categories
        categories = []
        for cat in entry.findall("atom:category", NAMESPACES):
            term = cat.get("term")
            if term:
                categories.append(term)
        paper["categories"] = categories

        # Extract authors
        authors = []
        for author in entry.findall("atom:author", NAMESPACES):
            name_elem = author.find("atom:name", NAMESPACES)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text)
        paper["authors"] = authors

        # Extract PDF link
        for link in entry.findall("atom:link", NAMESPACES):
            if link.get("title") == "pdf":
                paper["pdf_url"] = link.get("href")
                break

        papers.append(paper)

    return papers
