import requests
from providers.base import LLMProvider
from providers.factory import register


@register("llm", "openai")
class OpenAILLM(LLMProvider):
    """Client for any OpenAI-compatible /v1/chat/completions endpoint."""

    def chat(self, messages: list[dict]) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        resp = requests.post(
            f"{self.url}/v1/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": messages,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
