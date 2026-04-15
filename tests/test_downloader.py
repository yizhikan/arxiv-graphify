"""Tests for paper downloader."""
import json
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

    saved_path = save_paper_metadata(paper, str(papers_dir))

    # Check file was created
    paper_file = papers_dir / "2012.12104.json"
    assert paper_file.exists()

    loaded = load_paper_metadata(str(paper_file))
    assert loaded["title"] == "Test Paper"
    assert loaded["arxiv_id"] == "2012.12104"


def test_download_papers(tmp_path):
    """Test downloading multiple papers."""
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()

    papers = [
        {
            "arxiv_id": "2012.12104",
            "title": "Paper One",
            "abstract": "Abstract one",
        },
        {
            "arxiv_id": "2101.00001",
            "title": "Paper Two",
            "abstract": "Abstract two",
        },
    ]

    saved_files = download_papers(papers, str(papers_dir))

    assert len(saved_files) == 2
    assert (papers_dir / "2012.12104.json").exists()
    assert (papers_dir / "2101.00001.json").exists()


def test_download_papers_with_slash_in_id(tmp_path):
    """Test that slashes in arxiv_id are handled correctly."""
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()

    paper = {
        "arxiv_id": "2012.12104v1",
        "title": "Test Paper",
        "abstract": "Test abstract",
    }

    saved_path = save_paper_metadata(paper, str(papers_dir))

    # File should be created with cleaned filename
    assert Path(saved_path).exists()
