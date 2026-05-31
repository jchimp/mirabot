import requests
from providers.base import STTProvider
from providers.factory import register


@register("stt", "openai")
class OpenAISTT(STTProvider):
    """Client for the OpenAI Whisper /v1/audio/transcriptions endpoint."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        ext = "webm" if "webm" in mime_type else "wav"
        resp = requests.post(
            f"{self.url}/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            files={"file": (f"audio.{ext}", audio_bytes, mime_type)},
            data={"model": self.model or "whisper-1"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()
