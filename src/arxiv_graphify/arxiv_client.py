"""arXiv paper search client with multiple backends for China access.

Supported backends:
- arxiv: Official arXiv API (https://export.arxiv.org/api/query)
- openalex: OpenAlex API (https://api.openalex.org) - Better for China access

OpenAlex is a free, open index of scholarly papers that includes arXiv papers.
API Docs: https://docs.openalex.org
"""
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta


# arXiv category to OpenAlex topic mapping
ARXIV_TO_OPENALEX_TOPIC = {
    "cs.LG": "https://openalex.org/T42208696",  # Machine learning
    "cs.AI": "https://openalex.org/T41139496",  # Artificial intelligence
    "cs.CL": "https://openalex.org/T42043378",  # Computational linguistics/NLP
    "cs.CV": "https://openalex.org/T41013516",  # Computer vision
    "cs.NE": "https://openalex.org/T41125689",  # Neural and evolution computing
    "cs.SI": "https://openalex.org/T42101328",  # Social and information networks
    "stat.ML": "https://openalex.org/T42208696",  # Statistics + ML
}

# arXiv category to OpenAlex primary location source
ARXIV_TO_OPENALEX_SOURCE = {
    "cs.LG": "Computer Science",
    "cs.AI": "Computer Science",
    "cs.CL": "Computer Science",
    "cs.CV": "Computer Science",
    "cs.NE": "Computer Science",
    "cs.SI": "Computer Science",
    "stat.ML": "Mathematics",
}


# arXiv Source ID in OpenAlex
OPENALEX_ARXIV_SOURCE_ID = "https://openalex.org/S4306400194"  # arXiv (Cornell University)


class ArxivClient:
    """Client for arXiv papers with multiple backend support.

    Backends:
        - "arxiv": Official arXiv API (may have rate limits in China)
        - "openalex": OpenAlex API (free, better China access, recommended)

    Usage:
        # Use OpenAlex (recommended for China)
        client = ArxivClient(backend="openalex")

        # Use official arXiv API
        client = ArxivClient(backend="arxiv")
    """

    def __init__(
        self,
        backend: str = "openalex",  # "openalex" or "arxiv"
        timeout: int = 30,
        rate_limit: int = 1,  # OpenAlex allows higher rate
    ):
        """
        Initialize arXiv client.

        Args:
            backend: "openalex" for OpenAlex API, "arxiv" for official API
            timeout: Request timeout in seconds
            rate_limit: Seconds between requests to avoid rate limiting
        """
        self.backend = backend
        self.timeout = timeout
        self.rate_limit = rate_limit
        self._last_request_time: float = 0

        if backend == "openalex":
            self.api_base = "https://api.openalex.org/works"
            print(f"Using OpenAlex API: {self.api_base}")
            print(f"  -> Filtering for arXiv papers only")
        else:
            self.api_base = "https://export.arxiv.org/api/query"
            print(f"Using official arXiv API: {self.api_base}")

    def _wait_for_rate_limit(self):
        """Wait to respect rate limit between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request_time = time.time()

    def search(
        self,
        category: str,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100,
        start: int = 0,  # Used as page offset for OpenAlex
    ) -> List[Dict]:
        """
        Search arXiv papers.

        Args:
            category: arXiv category (e.g., "cs.AI", "cs.LG")
            keyword: Optional keyword to search in title/abstract
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_results: Maximum number of results to return
            start: Offset for pagination (page number for OpenAlex)

        Returns:
            List of paper dicts with metadata
        """
        if self.backend == "openalex":
            return self._search_openalex(
                category=category,
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                per_page=min(max_results, 200),  # OpenAlex max per page
                page=start + 1,  # OpenAlex uses 1-indexed pages
            )
        else:
            return self._search_arxiv(
                category=category,
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                max_results=max_results,
                start=start,
            )

    def _search_arxiv(
        self,
        category: str,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: int = 100,
        start: int = 0,
    ) -> List[Dict]:
        """Search using official arXiv API."""
        # Build search query
        query_parts = [f"cat:{category}"]
        if keyword:
            query_parts.append(f"all:{keyword}")

        # Add date filter
        if start_date and end_date:
            query_parts.append(f"submittedDate:[{start_date} TO {end_date}]")

        search_query = " AND ".join(query_parts)

        # Build URL parameters
        params = {
            "search_query": search_query,
            "start": start,
            "max_results": min(max_results, 100),
        }

        self._wait_for_rate_limit()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    self.api_base,
                    params=params,
                    timeout=self.timeout,
                    headers={"User-Agent": "arxiv-graphify/0.1.0"},
                )
                response.raise_for_status()
                return parse_arxiv_xml_response(response.text)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 30
                    print(f"  Rate limited (429), waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    raise
        return []

    def _search_openalex(
        self,
        category: str,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        per_page: int = 200,
        page: int = 1,
    ) -> List[Dict]:
        """Search using OpenAlex API, filtering for arXiv papers."""
        # Filter for arXiv source only
        filters = [f"primary_location.source.id:{OPENALEX_ARXIV_SOURCE_ID}"]

        # Build query
        if keyword:
            query = keyword
        else:
            query = None

        # Build URL parameters
        params = {
            "filter": ",".join(filters),
            "per_page": per_page,
            "page": page,
        }

        # Note: OpenAlex doesn't support select for all fields, so we get full response
        # Add date filter
        if start_date and end_date:
            params["filter"] += f",publication_date:{start_date}|{end_date}"

        self._wait_for_rate_limit()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    self.api_base,
                    params=params,
                    timeout=self.timeout,
                    headers={
                        "User-Agent": "arxiv-graphify/0.1.0",
                    },
                )
                response.raise_for_status()
                data = response.json()
                return parse_openalex_response(data)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 10
                    print(f"  Rate limited (429), waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"  HTTP Error {e.response.status_code}: {e.response.text[:200] if e.response else 'N/A'}")
                    raise
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"  Request failed, retrying...")
                    time.sleep(5)
                else:
                    raise
        return []

    def search_all(
        self,
        category: str,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: Optional[int] = 500,
        page_size: int = 100,
    ) -> List[Dict]:
        """
        Search arXiv papers with pagination.

        Args:
            category: arXiv category (e.g., "cs.AI", "cs.LG")
            keyword: Optional keyword to search in title/abstract
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_results: Total maximum results to fetch (None for unlimited)
            page_size: Results per page
        """
        all_papers = []
        current_page = 0
        max_pages = 100  # Safety limit

        if max_results is None:
            pages_needed = max_pages
        else:
            pages_needed = min((max_results + page_size - 1) // page_size, max_pages)

        print(f"    Fetching papers ({page_size} per page, up to {pages_needed} pages)...")

        for page in range(pages_needed):
            if max_results is not None:
                remaining = max_results - len(all_papers)
                if remaining <= 0:
                    break
                current_page_size = min(page_size, remaining)
            else:
                current_page_size = page_size

            print(f"    Page {page + 1}/{pages_needed}: fetching papers...")

            papers = self.search(
                category=category,
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                max_results=current_page_size,
                start=current_page,
            )

            if not papers:
                print(f"    No more papers found on page {page + 1}")
                break

            all_papers.extend(papers)
            print(f"    Got {len(papers)} papers, total: {len(all_papers)}")
            current_page += 1

            if len(papers) < current_page_size:
                break

        return all_papers

    def search_by_keywords(
        self,
        keywords: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results_per_keyword: Optional[int] = 100,
        page_size: int = 100,
    ) -> List[Dict]:
        """
        Search papers by multiple keywords with pagination.

        Args:
            keywords: List of arXiv keywords/categories
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_results_per_keyword: Max results per keyword (None for unlimited)
            page_size: Results per page for pagination

        Returns:
            List of unique paper dicts
        """
        all_papers = {}

        for i, keyword in enumerate(keywords):
            if i > 0:
                print(f"  Waiting {self.rate_limit}s before next keyword...")
                time.sleep(self.rate_limit)

            if "." in keyword:
                print(f"  Searching category: {keyword}")
                papers = self.search_all(
                    category=keyword,
                    max_results=max_results_per_keyword,
                    page_size=page_size,
                )
            else:
                papers = self.search_all(
                    category="cs.AI",
                    keyword=keyword,
                    max_results=max_results_per_keyword,
                    page_size=page_size,
                )

            for paper in papers:
                key = paper.get("arxiv_id") or paper.get("paper_id") or paper.get("id")
                if key:
                    all_papers[key] = paper

            print(f"  '{keyword}': {len(papers)} papers, total unique: {len(all_papers)}")

        return list(all_papers.values())


def parse_arxiv_xml_response(xml_text: str) -> List[Dict]:
    """Parse arXiv API XML response."""
    NAMESPACES = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall("atom:entry", NAMESPACES):
        paper = {}

        id_elem = entry.find("atom:id", NAMESPACES)
        if id_elem and id_elem.text:
            paper["arxiv_id"] = id_elem.text.split("/abs/")[-1]

        title_elem = entry.find("atom:title", NAMESPACES)
        if title_elem and title_elem.text:
            paper["title"] = title_elem.text.strip()

        summary_elem = entry.find("atom:summary", NAMESPACES)
        if summary_elem and summary_elem.text:
            paper["abstract"] = summary_elem.text.strip()

        published_elem = entry.find("atom:published", NAMESPACES)
        if published_elem and published_elem.text:
            paper["published"] = published_elem.text[:10]

        categories = []
        for cat in entry.findall("atom:category", NAMESPACES):
            term = cat.get("term")
            if term:
                categories.append(term)
        paper["categories"] = categories

        authors = []
        for author in entry.findall("atom:author", NAMESPACES):
            name_elem = author.find("atom:name", NAMESPACES)
            if name_elem and name_elem.text:
                authors.append(name_elem.text)
        paper["authors"] = authors

        for link in entry.findall("atom:link", NAMESPACES):
            if link.get("title") == "pdf":
                paper["pdf_url"] = link.get("href")
                break

        papers.append(paper)

    return papers


def parse_openalex_response(data: Dict) -> List[Dict]:
    """Parse OpenAlex API JSON response."""
    papers = []

    for work in data.get("results", []):
        paper = {}

        # Extract ID
        paper["id"] = work.get("id", "").split("/")[-1]

        # Extract title
        paper["title"] = work.get("title") or ""

        # Extract abstract (may be None)
        paper["abstract"] = work.get("abstract") or ""

        # Extract publication date
        pub_date = work.get("publication_date")
        if pub_date:
            paper["published"] = pub_date[:10]
        else:
            paper["published"] = ""

        # Extract authors
        authors = []
        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            if author.get("display_name"):
                authors.append(author["display_name"])
        paper["authors"] = authors[:10]  # Limit to first 10 authors

        # Extract arXiv info from primary_location
        primary_loc = work.get("primary_location", {}) or {}
        source = primary_loc.get("source", {}) or {}

        # Check if it's from arXiv
        if source.get("repository") == "arXiv":
            paper["arxiv_id"] = source.get("id", "").split("/")[-1]
            paper["pdf_url"] = f"https://arxiv.org/pdf/{paper['arxiv_id']}.pdf"
            paper["url"] = f"https://arxiv.org/abs/{paper['arxiv_id']}"
        else:
            # Try to get arXiv ID from open_access
            oa = work.get("open_access", {}) or {}
            oa_url = oa.get("oa_url")
            if oa_url and "arxiv.org" in oa_url:
                paper["arxiv_id"] = oa_url.split("/abs/")[-1].split("/")[-1]
                paper["pdf_url"] = f"https://arxiv.org/pdf/{paper['arxiv_id']}.pdf"
                paper["url"] = f"https://arxiv.org/abs/{paper['arxiv_id']}"
            else:
                paper["arxiv_id"] = ""
                paper["pdf_url"] = ""
                paper["url"] = work.get("landing_page_url") or ""

        # Extract categories (use primary topic as proxy)
        paper["categories"] = []
        primary_topic = primary_loc.get("source", {}).get("display_name") if primary_loc.get("source") else None
        if primary_topic:
            paper["categories"].append(primary_topic)

        # Only include papers with arXiv ID
        if paper.get("arxiv_id"):
            papers.append(paper)

    return papers


# Import ET at module level
import xml.etree.ElementTree as ET
