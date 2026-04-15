"""Tests for Qwen API client."""
import json
import pytest
from unittest.mock import patch, MagicMock
from arxiv_graphify.qwen_client import QwenClient, expand_keywords, generate_summary


@pytest.fixture
def client():
    """Create a test client with dummy API key."""
    return QwenClient(api_key="test-key")


def test_client_initialization(client):
    """Test client initializes with correct defaults."""
    assert client.api_key == "test-key"
    assert client.api_base == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert client.model == "qwen-plus"
    assert client.timeout == 60


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


@patch("arxiv_graphify.qwen_client.requests.Session.post")
def test_expand_keywords_mock(mock_post, client):
    """Mock test for keyword expansion."""
    import json as json_module
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"keywords": ["cs.LG", "cs.AI"]}'}}]
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    result = client.expand_keywords("test")

    assert mock_post.called
    call_args = mock_post.call_args
    assert "test" in call_args[1]["json"]["messages"][0]["content"]
