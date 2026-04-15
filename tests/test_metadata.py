"""Tests for metadata management."""
import json
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
    assert loaded.arxiv_keywords == ["cs.AI"]
    assert loaded.start_date == "2025-01-01"
    assert loaded.end_date == "2026-01-01"


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


def test_load_nonexistent_file():
    """Test loading metadata from nonexistent file returns None."""
    result = load_metadata("/nonexistent/path/.arxiv_meta.json")
    assert result is None


def test_update_timestamp_file_not_found():
    """Test updating timestamp for nonexistent file raises error."""
    try:
        update_metadata_timestamp("/nonexistent/path/.arxiv_meta.json")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass  # Expected
