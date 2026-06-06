import json
import requests
from providers.base import LLMProvider
from providers.factory import register


@register("llm", "openai")
class OpenAILLM(LLMProvider):
    """Client for any OpenAI-compatible /v1/chat/completions endpoint."""

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def chat(self, messages: list[dict]) -> str:
        resp = requests.post(
            f"{self.url}/v1/chat/completions",
            headers=self._headers(),
            json={"model": self.model, "messages": messages},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def chat_stream(self, messages: list[dict]):
        resp = requests.post(
            f"{self.url}/v1/chat/completions",
            headers=self._headers(),
            json={"model": self.model, "messages": messages, "stream": True},
            stream=True,
            timeout=120,
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            text = line.decode("utf-8") if isinstance(line, bytes) else line
            if not text.startswith("data: "):
                continue
            payload = text[6:]
            if payload.strip() == "[DONE]":
                break
            data = json.loads(payload)
            content = data["choices"][0].get("delta", {}).get("content", "")
            if content:
                yield content
