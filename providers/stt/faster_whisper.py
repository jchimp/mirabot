import requests
from providers.base import STTProvider
from providers.factory import register


@register("stt", "faster_whisper")
class FasterWhisperSTT(STTProvider):
    """
    Client for onerahmet/openai-whisper-asr-webservice
    running the faster_whisper engine.
    """

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        ext = "webm" if "webm" in mime_type else "wav"
        resp = requests.post(
            f"{self.url}/asr",
            files={"audio_file": (f"audio.{ext}", audio_bytes, mime_type)},
            params={
                "task": "transcribe",
                "language": "en",
                "output": "json",
                "encode": "true",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()
