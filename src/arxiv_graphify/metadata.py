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
