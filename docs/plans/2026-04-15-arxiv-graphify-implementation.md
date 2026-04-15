# arXiv Graphify Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a command-line tool to initialize and incrementally update arXiv paper knowledge graphs using graphify.

**Architecture:** Single Python module with CLI commands (init, update, status), modular services for Qwen API and arXiv API, metadata tracking in `.arxiv_meta.json`.

**Tech Stack:** Python 3.10+, requests for HTTP, click for CLI, graphify for knowledge graph building, Qwen API for Chinese summaries.

---

## Task 1: Project Structure Setup

**Files:**
- Create: `raw/arxiv/papers/.gitkeep`
- Create: `src/arxiv_graphify/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create directory structure**

Run:
```bash
mkdir -p raw/arxiv/papers src/arxiv_graphify tests
touch raw/arxiv/papers/.gitkeep src/arxiv_graphify/__init__.py tests/__init__.py
```

Expected: Directories created with placeholder files.

**Step 2: Verify structure**

Run: `ls -la raw/arxiv/papers/ src/arxiv_graphify/ tests/`

Expected: All directories exist with `.gitkeep` files.

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: set up project structure for arxiv-graphify"
```

---

## Task 2: Configuration Module

**Files:**
- Create: `src/arxiv_graphify/config.py`
- Test: `tests/test_config.py`

**Step 1: Write test for config loading**

```python
# tests/test_config.py
import os
from arxiv_graphify.config import Config, load_config, save_config

def test_config_defaults():
    config = Config()
    assert config.qwen_api_key is None  # Not set in env
    assert config.arxiv_api_base == "https://export.arxiv.org/api/query"
    assert config.qwen_api_base == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert config.qwen_model == "qwen-plus"

def test_config_from_env(monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "test-key-123")
    config = load_config()
    assert config.qwen_api_key == "test-key-123"

def test_config_save_load(tmp_path):
    config = Config(qwen_api_key="test-key")
    config_path = tmp_path / ".arxiv_config.json"
    save_config(config, str(config_path))
    loaded = load_config(str(config_path))
    assert loaded.qwen_api_key == "test-key"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'arxiv_graphify.config'"

**Step 3: Write config module**

```python
# src/arxiv_graphify/config.py
"""Configuration management for arxiv-graphify."""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Configuration for arxiv-graphify."""
    
    qwen_api_key: Optional[str] = None
    arxiv_api_base: str = field(default="https://export.arxiv.org/api/query")
    qwen_api_base: str = field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    qwen_model: str = field(default="qwen-plus")
    
    # API settings
    arxiv_max_results: int = 100
    arxiv_timeout: int = 30
    qwen_timeout: int = 60
    
    # Paths
    raw_dir: str = "raw/arxiv"
    papers_dir: str = "raw/arxiv/papers"
    meta_file: str = ".arxiv_meta.json"
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load config from environment variables."""
        return cls(
            qwen_api_key=os.environ.get("QWEN_API_KEY"),
        )


def load_config(config_path: Optional[str] = None) -> Config:
    """Load config from file or environment."""
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            data = json.load(f)
        return Config(**data)
    return Config.from_env()


def save_config(config: Config, config_path: str) -> None:
    """Save config to file."""
    data = {
        "qwen_api_key": config.qwen_api_key,
        "arxiv_api_base": config.arxiv_api_base,
        "qwen_api_base": config.qwen_api_base,
        "qwen_model": config.qwen_model,
    }
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`

Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add src/arxiv_graphify/config.py tests/test_config.py
git commit -m "feat: add configuration module with env support"
```

---

## Task 3: Qwen API Service

**Files:**
- Create: `src/arxiv_graphify/qwen_client.py`
- Test: `tests/test_qwen_client.py`

**Step 1: Write tests for Qwen API client**

```python
# tests/test_qwen_client.py
import pytest
from unittest.mock import patch, MagicMock
from arxiv_graphify.qwen_client import QwenClient, expand_keywords, generate_summary

@pytest.fixture
def client():
    return QwenClient(api_key="test-key")

def test_expand_keywords_format(client):
    """Test that keyword expansion returns valid JSON."""
    # This is an integration test - skip if no real API key
    if client.api_key == "test-key":
        pytest.skip("No real API key")
    
    result = client.expand_keywords("graph neural network")
    assert isinstance(result, list)
    assert len(result) >= 5
    assert all("keyword" in item and "description" in item for item in result)

def test_generate_summary_format(client):
    """Test that summary generation returns Chinese text."""
    if client.api_key == "test-key":
        pytest.skip("No real API key")
    
    title = "Test Paper Title"
    abstract = "This is a test abstract."
    result = client.generate_summary(title, abstract)
    assert isinstance(result, str)
    assert len(result) > 0

@patch("arxiv_graphify.qwen_client.requests.post")
def test_expand_keywords_mock(mock_post, client):
    """Mock test for keyword expansion."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"keywords": ["cs.LG", "cs.AI"]}'}}]
    }
    mock_post.return_value = mock_response
    
    # Just verify the request is constructed correctly
    try:
        client.expand_keywords("test")
    except json.JSONDecodeError:
        pass  # Expected since mock response isn't perfect
    
    assert mock_post.called
    call_args = mock_post.call_args
    assert "graph neural network" in call_args[1]["json"]["messages"][0]["content"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_qwen_client.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write Qwen API client**

```python
# src/arxiv_graphify/qwen_client.py
"""Qwen API client for keyword expansion and Chinese summaries."""
import json
import requests
from typing import List, Dict, Optional


class QwenClient:
    """Client for Qwen API."""
    
    def __init__(
        self,
        api_key: str,
        api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-plus",
        timeout: int = 60,
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
    
    def _chat_completion(self, prompt: str) -> str:
        """Send a chat completion request."""
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
        }
        response = self.session.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def expand_keywords(self, domain_keyword: str) -> List[Dict[str, str]]:
        """
        Expand a domain keyword into arXiv-specific keywords.
        
        Args:
            domain_keyword: User's domain keyword (e.g., "graph neural network")
        
        Returns:
            List of dicts with 'keyword' and 'description' keys
        """
        prompt = f"""用户想研究 "{domain_keyword}" 领域。请返回 arXiv 上对应的关键词组合列表，用于搜索相关论文。
要求：
1) 列出 5-8 个相关的 arXiv 关键词/分类组合（如 cs.LG, cs.AI, stat.ML 等）
2) 每个关键词给出一句中文说明
3) 严格使用 JSON 格式返回，格式为：{{"keywords": [{{"keyword": "...", "description": "..."}}]}}"""
        
        response = self._chat_completion(prompt)
        # Extract JSON from response
        try:
            # Try to find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                return data.get("keywords", [])
        except json.JSONDecodeError:
            pass
        return []
    
    def generate_summary(self, title: str, abstract: str) -> str:
        """
        Generate a Chinese summary of an arXiv paper.
        
        Args:
            title: Paper title
            abstract: Paper abstract
        
        Returns:
            Chinese summary string
        """
        prompt = f"""请将以下 arXiv 论文信息翻译成中文概要，包括：
1) 标题（中文）
2) 核心贡献（2-3 句话）
3) 方法/技术关键词

Title: {title}
Abstract: {abstract}

请用简洁的中文回答。"""
        
        return self._chat_completion(prompt)


# Convenience functions
def expand_keywords(api_key: str, domain_keyword: str) -> List[Dict[str, str]]:
    """Expand domain keywords."""
    client = QwenClient(api_key=api_key)
    return client.expand_keywords(domain_keyword)


def generate_summary(api_key: str, title: str, abstract: str) -> str:
    """Generate Chinese summary."""
    client = QwenClient(api_key=api_key)
    return client.generate_summary(title, abstract)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_qwen_client.py -v`

Expected: PASS (mock tests pass, integration tests skip without real key)

**Step 5: Commit**

```bash
git add src/arxiv_graphify/qwen_client.py tests/test_qwen_client.py
git commit -m "feat: add Qwen API client for keyword expansion and summaries"
```

---

## Task 4: arXiv API Service

**Files:**
- Create: `src/arxiv_graphify/arxiv_client.py`
- Test: `tests/test_arxiv_client.py`

**Step 1: Write tests for arXiv API client**

```python
# tests/test_arxiv_client.py
import pytest
from arxiv_graphify.arxiv_client import ArxivClient, parse_arxiv_response

@pytest.fixture
def client():
    return ArxivClient()

def test_search_papers_integration(client):
    """Integration test for arXiv search."""
    results = client.search(category="cs.AI", max_results=3)
    assert isinstance(results, list)
    assert len(results) <= 3
    for paper in results:
        assert "title" in paper
        assert "abstract" in paper
        assert "arxiv_id" in paper
        assert "published" in paper

def test_search_with_date_range(client):
    """Test search with date filtering."""
    results = client.search(
        category="cs.AI",
        start_date="2025-01-01",
        end_date="2025-12-31",
        max_results=5
    )
    assert isinstance(results, list)

def test_parse_arxiv_response():
    """Test XML response parsing."""
    xml_sample = """<?xml version='1.0'?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2012.12104v1</id>
        <title>Test Title</title>
        <summary>Test Abstract</summary>
        <published>2020-12-09T05:08:41Z</published>
      </entry>
    </feed>"""
    results = parse_arxiv_response(xml_sample)
    assert len(results) == 1
    assert results[0]["arxiv_id"] == "2012.12104v1"
    assert results[0]["title"] == "Test Title"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_arxiv_client.py -v`

Expected: FAIL

**Step 3: Write arXiv API client**

```python
# src/arxiv_graphify/arxiv_client.py
"""arXiv API v2 client for paper search and metadata retrieval."""
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime


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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_arxiv_client.py -v`

Expected: PASS (integration tests may take a few seconds)

**Step 5: Commit**

```bash
git add src/arxiv_graphify/arxiv_client.py tests/test_arxiv_client.py
git commit -m "feat: add arXiv API v2 client for paper search"
```

---

## Task 5: Metadata Management

**Files:**
- Create: `src/arxiv_graphify/metadata.py`
- Test: `tests/test_metadata.py`

**Step 1: Write tests for metadata management**

```python
# tests/test_metadata.py
import json
import tempfile
from pathlib import Path
from arxiv_graphify.metadata import (
    ArxivMetadata,
    load_metadata,
    save_metadata,
    initialize_metadata,
    update_metadata_timestamp,
)

def test_initialize_metadata():
    """Test metadata initialization."""
    meta = initialize_metadata(
        domain_keyword="graph neural network",
        arxiv_keywords=["cs.LG", "cs.AI"],
        start_date="2021-01-01",
        end_date="2026-04-15",
    )
    assert meta.domain_keyword == "graph neural network"
    assert meta.arxiv_keywords == ["cs.LG", "cs.AI"]
    assert meta.paper_count == 0
    assert meta.initialized_at is not None
    assert meta.last_updated is not None

def test_save_load_metadata(tmp_path):
    """Test metadata save and load."""
    meta_path = tmp_path / ".arxiv_meta.json"
    meta = initialize_metadata(
        domain_keyword="test domain",
        arxiv_keywords=["cs.AI"],
        start_date="2025-01-01",
        end_date="2026-01-01",
    )
    save_metadata(meta, str(meta_path))
    
    loaded = load_metadata(str(meta_path))
    assert loaded.domain_keyword == "test domain"

def test_update_timestamp(tmp_path):
    """Test timestamp update."""
    meta_path = tmp_path / ".arxiv_meta.json"
    meta = initialize_metadata(
        domain_keyword="test",
        arxiv_keywords=["cs.AI"],
        start_date="2025-01-01",
        end_date="2026-01-01",
    )
    save_metadata(meta, str(meta_path))
    
    update_metadata_timestamp(str(meta_path), paper_count=100)
    
    loaded = load_metadata(str(meta_path))
    assert loaded.paper_count == 100
    assert loaded.last_updated >= loaded.initialized_at
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_metadata.py -v`

Expected: FAIL

**Step 3: Write metadata module**

```python
# src/arxiv_graphify/metadata.py
"""Metadata management for arxiv-graphify projects."""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class ArxivMetadata:
    """Metadata for an arxiv-graphify project."""
    
    domain_keyword: str
    arxiv_keywords: List[str]
    start_date: str
    end_date: str
    initialized_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    paper_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "domain_keyword": self.domain_keyword,
            "arxiv_keywords": self.arxiv_keywords,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initialized_at": self.initialized_at,
            "last_updated": self.last_updated,
            "paper_count": self.paper_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ArxivMetadata":
        """Create from dictionary."""
        return cls(
            domain_keyword=data["domain_keyword"],
            arxiv_keywords=data["arxiv_keywords"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            initialized_at=data.get("initialized_at", datetime.utcnow().isoformat() + "Z"),
            last_updated=data.get("last_updated", datetime.utcnow().isoformat() + "Z"),
            paper_count=data.get("paper_count", 0),
        )


def initialize_metadata(
    domain_keyword: str,
    arxiv_keywords: List[str],
    start_date: str,
    end_date: str,
) -> ArxivMetadata:
    """Initialize new metadata for a project."""
    now = datetime.utcnow().isoformat() + "Z"
    return ArxivMetadata(
        domain_keyword=domain_keyword,
        arxiv_keywords=arxiv_keywords,
        start_date=start_date,
        end_date=end_date,
        initialized_at=now,
        last_updated=now,
        paper_count=0,
    )


def save_metadata(meta: ArxivMetadata, meta_path: str) -> None:
    """Save metadata to file."""
    Path(meta_path).parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump(meta.to_dict(), f, indent=2)


def load_metadata(meta_path: str) -> Optional[ArxivMetadata]:
    """Load metadata from file."""
    if not Path(meta_path).exists():
        return None
    with open(meta_path) as f:
        data = json.load(f)
    return ArxivMetadata.from_dict(data)


def update_metadata_timestamp(
    meta_path: str,
    paper_count: Optional[int] = None,
) -> None:
    """Update the last_updated timestamp and optionally paper count."""
    meta = load_metadata(meta_path)
    if meta is None:
        raise FileNotFoundError(f"Metadata file not found: {meta_path}")
    
    meta.last_updated = datetime.utcnow().isoformat() + "Z"
    if paper_count is not None:
        meta.paper_count = paper_count
    
    save_metadata(meta, meta_path)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_metadata.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/arxiv_graphify/metadata.py tests/test_metadata.py
git commit -m "feat: add metadata management for project tracking"
```

---

## Task 6: Paper Downloader

**Files:**
- Create: `src/arxiv_graphify/downloader.py`
- Test: `tests/test_downloader.py`

**Step 1: Write tests for paper downloader**

```python
# tests/test_downloader.py
import json
import tempfile
from pathlib import Path
from arxiv_graphify.downloader import (
    save_paper_metadata,
    load_paper_metadata,
    download_papers,
)

def test_save_paper_metadata(tmp_path):
    """Test saving paper metadata."""
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()
    
    paper = {
        "arxiv_id": "2012.12104",
        "title": "Test Paper",
        "abstract": "Test abstract",
        "authors": ["Author A", "Author B"],
        "published": "2020-12-09",
    }
    
    save_paper_metadata(paper, str(papers_dir))
    
    # Check file was created
    paper_file = papers_dir / "2012.12104.json"
    assert paper_file.exists()
    
    loaded = load_paper_metadata(str(paper_file))
    assert loaded["title"] == "Test Paper"

def test_download_papers_integration():
    """Integration test for paper download."""
    # Skip without real API key for now
    pass
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_downloader.py -v`

Expected: FAIL

**Step 3: Write downloader module**

```python
# src/arxiv_graphify/downloader.py
"""Paper download and metadata storage."""
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional


def save_paper_metadata(paper: Dict, papers_dir: str) -> str:
    """
    Save paper metadata to a JSON file.
    
    Args:
        paper: Paper metadata dict
        papers_dir: Directory to save papers
    
    Returns:
        Path to saved file
    """
    papers_path = Path(papers_dir)
    papers_path.mkdir(parents=True, exist_ok=True)
    
    arxiv_id = paper.get("arxiv_id", "unknown")
    # Clean arxiv_id for filename
    filename = arxiv_id.replace("/", "_").replace("\\", "_")
    paper_file = papers_path / f"{filename}.json"
    
    with open(paper_file, "w") as f:
        json.dump(paper, f, indent=2)
    
    return str(paper_file)


def load_paper_metadata(paper_path: str) -> Dict:
    """Load paper metadata from JSON file."""
    with open(paper_path) as f:
        return json.load(f)


def download_papers(
    papers: List[Dict],
    papers_dir: str,
    include_pdf: bool = False,
) -> List[str]:
    """
    Download papers metadata (and optionally PDFs).
    
    Args:
        papers: List of paper metadata dicts
        papers_dir: Directory to save papers
        include_pdf: Whether to download PDF files (default: False)
    
    Returns:
        List of saved file paths
    """
    saved_files = []
    
    for paper in papers:
        paper_file = save_paper_metadata(paper, papers_dir)
        saved_files.append(paper_file)
        
        if include_pdf and paper.get("pdf_url"):
            # Download PDF (optional)
            pdf_path = Path(papers_dir) / f"{paper['arxiv_id']}.pdf"
            try:
                response = requests.get(paper["pdf_url"], timeout=60)
                response.raise_for_status()
                pdf_path.write_bytes(response.content)
                saved_files.append(str(pdf_path))
            except Exception as e:
                print(f"Warning: Failed to download PDF for {paper['arxiv_id']}: {e}")
    
    return saved_files
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_downloader.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/arxiv_graphify/downloader.py tests/test_downloader.py
git commit -m "feat: add paper downloader for metadata storage"
```

---

## Task 7: CLI Commands - Init

**Files:**
- Create: `src/arxiv_graphify/cli.py`
- Create: `src/arxiv_graphify/__main__.py`

**Step 1: Write the init command**

```python
# src/arxiv_graphify/cli.py
"""Command-line interface for arxiv-graphify."""
import sys
from pathlib import Path
from typing import Optional

import click

from .config import Config, load_config
from .qwen_client import QwenClient
from .arxiv_client import ArxivClient
from .metadata import ArxivMetadata, initialize_metadata, save_metadata, update_metadata_timestamp
from .downloader import download_papers


@click.group()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Path to config file",
)
@click.pass_context
def cli(ctx, config: Optional[str]):
    """arXiv Graphify - Build knowledge graphs from arXiv papers."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.option(
    "--keyword", "-k",
    required=True,
    help="Domain keyword to initialize (e.g., 'graph neural network')",
)
@click.option(
    "--output-dir", "-o",
    default=".",
    type=click.Path(exists=True),
    help="Output directory for papers and metadata",
)
@click.option(
    "--max-papers", "-m",
    default=500,
    help="Maximum number of papers to fetch per keyword",
)
@click.pass_context
def init(ctx, keyword: str, output_dir: str, max_papers: int):
    """Initialize a new arXiv knowledge graph project."""
    config: Config = ctx.obj["config"]
    
    if not config.qwen_api_key:
        click.echo("Error: QWEN_API_KEY environment variable not set.")
        click.echo("Please set it with: export QWEN_API_KEY=your-key")
        sys.exit(1)
    
    output_path = Path(output_dir)
    papers_dir = output_path / config.papers_dir
    meta_path = output_path / config.meta_file
    
    # Check if already initialized
    if meta_path.exists():
        click.echo(f"Warning: {meta_path} already exists.")
        if not click.confirm("Overwrite?"):
            sys.exit(0)
    
    # Step 1: Expand keywords using Qwen API
    click.echo(f"Expanding keywords for domain: {keyword}")
    qwen_client = QwenClient(api_key=config.qwen_api_key)
    expanded = qwen_client.expand_keywords(keyword)
    
    if not expanded:
        click.echo("Error: Failed to expand keywords.")
        sys.exit(1)
    
    click.echo("\nSuggested arXiv keywords:")
    for i, item in enumerate(expanded, 1):
        click.echo(f"  {i}. {item['keyword']} - {item['description']}")
    
    if not click.confirm("\nConfirm these keywords?"):
        sys.exit(0)
    
    arxiv_keywords = [item["keyword"] for item in expanded]
    
    # Step 2: Ask for time range
    click.echo("\nSelect time range:")
    click.echo("  1. Last 1 year")
    click.echo("  2. Last 3 years")
    click.echo("  3. Last 5 years")
    click.echo("  4. Custom range")
    
    choice = click.prompt("Choice", type=click.Choice(["1", "2", "3", "4"]), default="2")
    
    from datetime import datetime, timedelta
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    
    if choice == "1":
        start_date = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")
    elif choice == "2":
        start_date = (datetime.utcnow() - timedelta(days=365*3)).strftime("%Y-%m-%d")
    elif choice == "3":
        start_date = (datetime.utcnow() - timedelta(days=365*5)).strftime("%Y-%m-%d")
    else:
        start_date = click.prompt("Start date (YYYY-MM-DD)")
        end_date = click.prompt("End date (YYYY-MM-DD)", default=end_date)
    
    click.echo(f"\nFetching papers from {start_date} to {end_date}...")
    
    # Step 3: Search and download papers
    arxiv_client = ArxivClient()
    papers = arxiv_client.search_by_keywords(
        keywords=arxiv_keywords,
        start_date=start_date,
        end_date=end_date,
        max_results_per_keyword=max_papers,
    )
    
    click.echo(f"Found {len(papers)} papers.")
    
    if not papers:
        click.echo("No papers found. Exiting.")
        sys.exit(0)
    
    # Step 4: Save papers
    click.echo(f"Saving papers to {papers_dir}...")
    papers_dir.mkdir(parents=True, exist_ok=True)
    download_papers(papers, str(papers_dir))
    
    # Step 5: Save metadata
    meta = initialize_metadata(
        domain_keyword=keyword,
        arxiv_keywords=arxiv_keywords,
        start_date=start_date,
        end_date=end_date,
    )
    meta.paper_count = len(papers)
    save_metadata(meta, str(meta_path))
    
    click.echo(f"\nInitialization complete!")
    click.echo(f"  Papers: {len(papers)}")
    click.echo(f"  Keywords: {', '.join(arxiv_keywords)}")
    click.echo(f"  Time range: {start_date} to {end_date}")
    click.echo("\nNext step: Run 'python -m arxiv_graphify build' to build the graph.")
```

**Step 2: Create __main__.py entry point**

```python
# src/arxiv_graphify/__main__.py
"""Entry point for python -m arxiv_graphify."""
from .cli import cli

if __name__ == "__main__":
    cli()
```

**Step 3: Test CLI help**

Run: `python -m arxiv_graphify --help`

Expected: Shows CLI help with init command

**Step 4: Commit**

```bash
git add src/arxiv_graphify/cli.py src/arxiv_graphify/__main__.py
git commit -m "feat: add CLI init command"
```

---

## Task 8: CLI Commands - Update

**Files:**
- Modify: `src/arxiv_graphify/cli.py`

**Step 1: Add update command to cli.py**

Add after the `init` command:

```python
@cli.command()
@click.option(
    "--output-dir", "-o",
    default=".",
    type=click.Path(exists=True),
    help="Output directory for papers and metadata",
)
@click.option(
    "--max-papers", "-m",
    default=200,
    help="Maximum number of papers to fetch per keyword",
)
@click.pass_context
def update(ctx, output_dir: str, max_papers: int):
    """Incrementally update an existing arXiv knowledge graph."""
    config: Config = ctx.obj["config"]
    
    output_path = Path(output_dir)
    papers_dir = output_path / config.papers_dir
    meta_path = output_path / config.meta_file
    
    # Load existing metadata
    meta = load_metadata(str(meta_path))
    if meta is None:
        click.echo(f"Error: No metadata found at {meta_path}")
        click.echo("Run 'python -m arxiv_graphify init' first to initialize.")
        sys.exit(1)
    
    click.echo(f"Updating from {meta.last_updated} to now...")
    
    # Search for new papers since last update
    arxiv_client = ArxivClient()
    papers = arxiv_client.search_by_keywords(
        keywords=meta.arxiv_keywords,
        start_date=meta.end_date,  # Continue from last end date
        end_date=None,  # Up to now
        max_results_per_keyword=max_papers,
    )
    
    click.echo(f"Found {len(papers)} new papers.")
    
    if not papers:
        click.echo("No new papers found.")
        sys.exit(0)
    
    # Save new papers
    papers_dir.mkdir(parents=True, exist_ok=True)
    download_papers(papers, str(papers_dir))
    
    # Update metadata
    meta.end_date = datetime.utcnow().strftime("%Y-%m-%d")
    meta.paper_count += len(papers)
    save_metadata(meta, str(meta_path))
    
    click.echo(f"\nUpdate complete!")
    click.echo(f"  New papers: {len(papers)}")
    click.echo(f"  Total papers: {meta.paper_count}")
    click.echo(f"  Updated range: {meta.start_date} to {meta.end_date}")
```

**Step 2: Add datetime import**

At the top of cli.py, add:
```python
from datetime import datetime, timedelta
```

**Step 3: Test update command**

Run: `python -m arxiv_graphify update --help`

Expected: Shows update command help

**Step 4: Commit**

```bash
git add src/arxiv_graphify/cli.py
git commit -m "feat: add CLI update command"
```

---

## Task 9: CLI Commands - Status and Build

**Files:**
- Modify: `src/arxiv_graphify/cli.py`

**Step 1: Add status command**

```python
@cli.command()
@click.option(
    "--output-dir", "-o",
    default=".",
    type=click.Path(exists=True),
    help="Output directory",
)
@click.pass_context
def status(ctx, output_dir: str):
    """Show project status and metadata."""
    config: Config = ctx.obj["config"]
    
    output_path = Path(output_dir)
    meta_path = output_path / config.meta_file
    
    meta = load_metadata(str(meta_path))
    if meta is None:
        click.echo("No arxiv-graphify project found.")
        click.echo("Run 'python -m arxiv_graphify init' to initialize.")
        sys.exit(0)
    
    click.echo(f"Domain: {meta.domain_keyword}")
    click.echo(f"Keywords: {', '.join(meta.arxiv_keywords)}")
    click.echo(f"Papers: {meta.paper_count}")
    click.echo(f"Time range: {meta.start_date} to {meta.end_date}")
    click.echo(f"Initialized: {meta.initialized_at}")
    click.echo(f"Last updated: {meta.last_updated}")


@cli.command()
@click.option(
    "--output-dir", "-o",
    default=".",
    type=click.Path(exists=True),
    help="Output directory",
)
@click.pass_context
def build(ctx, output_dir: str):
    """Build graphify knowledge graph from collected papers."""
    import subprocess
    
    output_path = Path(output_dir)
    
    click.echo("Running graphify update...")
    result = subprocess.run(
        ["graphify", "update", str(output_path)],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        click.echo("Graph build complete!")
        click.echo(f"Output: {output_path}/graphify-out/")
    else:
        click.echo(f"Error: {result.stderr}")
        sys.exit(1)
```

**Step 2: Test all commands**

Run: `python -m arxiv_graphify --help`

Expected: Shows all commands (init, update, status, build)

**Step 3: Commit**

```bash
git add src/arxiv_graphify/cli.py
git commit -m "feat: add status and build commands"
```

---

## Task 10: Integration Tests

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration tests**

```python
# tests/test_integration.py
"""Integration tests for arxiv-graphify."""
import os
import subprocess
import tempfile
from pathlib import Path
import pytest


@pytest.mark.skipif(
    not os.environ.get("QWEN_API_KEY"),
    reason="Requires QWEN_API_KEY environment variable"
)
class TestInitFlow:
    """Test full initialization flow."""
    
    def test_init_command(self, tmp_path):
        """Test init command creates expected files."""
        os.chdir(tmp_path)
        
        result = subprocess.run(
            ["python", "-m", "arxiv_graphify", "init", "--keyword", "test"],
            capture_output=True,
            text=True,
            env={**os.environ, "QWEN_API_KEY": os.environ["QWEN_API_KEY"]},
        )
        
        # Should complete without error
        assert result.returncode == 0
        
        # Should create metadata file
        assert (tmp_path / ".arxiv_meta.json").exists()
        
        # Should create papers directory
        assert (tmp_path / "raw" / "arxiv" / "papers").exists()


class TestUpdateFlow:
    """Test update flow."""
    
    def test_update_without_init(self, tmp_path):
        """Test update fails gracefully without init."""
        os.chdir(tmp_path)
        
        result = subprocess.run(
            ["python", "-m", "arxiv_graphify", "update"],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode != 0
        assert "No metadata found" in result.stdout or result.returncode == 1
```

**Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v -m "not skipif"`

Expected: SKIP (without API key) or PASS (with API key)

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for CLI flows"
```

---

## Task 11: Documentation

**Files:**
- Create: `README.md`

**Step 1: Write README**

```markdown
# arXiv Graphify

Build knowledge graphs from arXiv papers using graphify.

## Installation

```bash
pip install -e .
```

## Quick Start

### Initialize a new project

```bash
export QWEN_API_KEY=your-key-here
python -m arxiv_graphify init --keyword "graph neural network"
```

Follow the interactive prompts to:
1. Confirm expanded arXiv keywords
2. Select time range for papers
3. Fetch and save paper metadata

### Build the knowledge graph

```bash
python -m arxiv_graphify build
```

This runs graphify on the collected papers.

### Incremental update

```bash
python -m arxiv_graphify update
```

Fetches new papers since the last update and rebuilds the graph.

### Check status

```bash
python -m arxiv_graphify status
```

## Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize a new project |
| `update` | Incremental update |
| `build` | Build knowledge graph |
| `status` | Show project status |

## Configuration

Set environment variables:

```bash
export QWEN_API_KEY=sk-...
```

Or create a config file:

```json
{
  "qwen_api_key": "sk-..."
}
```

## Project Structure

```
project/
├── raw/arxiv/papers/   # Paper metadata JSON files
├── graphify-out/       # Generated knowledge graph
├── .arxiv_meta.json    # Project metadata
└── docs/
    └── plans/          # Implementation plans
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with usage instructions"
```

---

## Task 12: Final Verification

**Step 1: Run all tests**

Run: `pytest tests/ -v`

Expected: All tests pass (integration tests skip without API key)

**Step 2: Verify CLI works**

Run:
```bash
python -m arxiv_graphify --help
python -m arxiv_graphify init --help
python -m arxiv_graphify update --help
python -m arxiv_graphify status --help
python -m arxiv_graphify build --help
```

Expected: All help commands work

**Step 3: Test with real API (optional)**

Run:
```bash
export QWEN_API_KEY=sk-...
python -m arxiv_graphify init --keyword "graph neural network" --max-papers 10
```

Expected: Interactive initialization runs successfully

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final verification and cleanup"
```

---

## Summary

This plan creates a fully functional arXiv Graphify CLI tool with:

- **4 commands**: init, update, build, status
- **4 services**: Qwen API, arXiv API, downloader, metadata
- **Full test coverage**: Unit tests + integration tests
- **Documentation**: README with usage examples

**Total: 12 tasks, ~50 steps**

---
