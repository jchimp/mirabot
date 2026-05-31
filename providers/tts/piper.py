import requests
from providers.base import TTSProvider
from providers.factory import register


@register("tts", "piper")
class PiperTTS(TTSProvider):
    """Client for our custom Piper HTTP server."""

    def synthesize(self, text: str) -> bytes:
        resp = requests.post(
            f"{self.url}/synthesize",
            json={"text": text, "voice": self.voice},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.content  # raw WAV bytes
