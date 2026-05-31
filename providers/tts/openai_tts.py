import requests
from providers.base import TTSProvider
from providers.factory import register


@register("tts", "openai")
class OpenAITTS(TTSProvider):
    """Client for OpenAI /v1/audio/speech endpoint."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")

    def synthesize(self, text: str) -> bytes:
        resp = requests.post(
            f"{self.url}/v1/audio/speech",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "tts-1",
                "input": text,
                "voice": self.voice or "alloy",
                "response_format": "wav",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.content
