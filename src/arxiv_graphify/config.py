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
