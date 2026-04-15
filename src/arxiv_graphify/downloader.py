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
