"""Tests for configuration module."""
import os
import json
from pathlib import Path
from arxiv_graphify.config import Config, load_config, save_config


def test_config_defaults():
    """Test config default values."""
    config = Config()
    assert config.qwen_api_key is None  # Not set in env
    assert config.arxiv_api_base == "https://export.arxiv.org/api/query"
    assert config.qwen_api_base == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert config.qwen_model == "qwen-plus"


def test_config_from_env(monkeypatch):
    """Test loading config from environment."""
    monkeypatch.setenv("QWEN_API_KEY", "test-key-123")
    config = load_config()
    assert config.qwen_api_key == "test-key-123"


def test_config_save_load(tmp_path):
    """Test saving and loading config from file."""
    config = Config(qwen_api_key="test-key")
    config_path = tmp_path / ".arxiv_config.json"
    save_config(config, str(config_path))
    loaded = load_config(str(config_path))
    assert loaded.qwen_api_key == "test-key"
