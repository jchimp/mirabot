import requests
from providers.base import LLMProvider
from providers.factory import register


@register("llm", "ollama")
class OllamaLLM(LLMProvider):
    """Client for Ollama /api/chat endpoint."""

    def chat(self, messages: list[dict]) -> str:
        resp = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    def health(self) -> bool:
        try:
            r = requests.get(f"{self.url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False
