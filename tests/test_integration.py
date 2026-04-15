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
            env={**os.environ, "PYTHONPATH": "/mnt/d/wsl2/graphify/src"},
        )

        assert result.returncode != 0
        assert "No metadata found" in result.stdout or result.returncode == 1


class TestStatusFlow:
    """Test status flow."""

    def test_status_without_init(self, tmp_path):
        """Test status shows appropriate message without init."""
        os.chdir(tmp_path)

        result = subprocess.run(
            ["python", "-m", "arxiv_graphify", "status"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": "/mnt/d/wsl2/graphify/src"},
        )

        assert "No arxiv-graphify project found" in result.stdout
