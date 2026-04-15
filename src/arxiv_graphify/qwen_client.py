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
