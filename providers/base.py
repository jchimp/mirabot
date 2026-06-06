"""
Abstract base classes — the contracts every provider must fulfill.
Add a new service type by adding a new ABC here.
"""
from abc import ABC, abstractmethod
import requests


class STTProvider(ABC):
    """Speech-to-Text: audio bytes in, text out."""

    def __init__(self, config: dict):
        self.url = config.get("url", "")
        self.model = config.get("model", "")

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        ...

    def health(self) -> bool:
        try:
            r = requests.get(self.url, timeout=3)
            return r.status_code < 500
        except Exception:
            return False


class TTSProvider(ABC):
    """Text-to-Speech: text in, WAV bytes out."""

    def __init__(self, config: dict):
        self.url = config.get("url", "")
        self.voice = config.get("voice", "")

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        ...

    def health(self) -> bool:
        try:
            r = requests.get(f"{self.url}/health", timeout=3)
            return r.status_code == 200
        except Exception:
            return False


class LLMProvider(ABC):
    """Large Language Model: message list in, response text out."""

    def __init__(self, config: dict):
        self.url = config.get("url", "")
        self.model = config.get("model", "")
        self.api_key = config.get("api_key", "")

    @abstractmethod
    def chat(self, messages: list[dict]) -> str:
        ...

    def chat_stream(self, messages: list[dict]):
        """Yield response tokens. Default: single chunk from non-streaming chat()."""
        yield self.chat(messages)

    def health(self) -> bool:
        try:
            r = requests.get(self.url, timeout=3)
            return r.status_code < 500
        except Exception:
            return False

class CalendarProvider(ABC):
    """Calendar provider interface — read-only access to user's calendar."""

    def __init__(self, config: dict):
        self.timezone = config.get("timezone", "America/Denver")
        self.lookahead_days = config.get("lookahead_days", 3)

    @abstractmethod
    def authenticate_interactive(self, token_store) -> bool:
        """Run interactive CLI auth flow. Returns True on success."""
        ...

    @abstractmethod
    def get_events(self, start, end, token_store) -> list[dict]:
        """
        Fetch calendar events in the given time range.
        Returns list of:
            {
                "summary": str,
                "start": str (ISO),
                "end": str (ISO),
                "location": str,
                "all_day": bool,
            }
        """
        ...

    @abstractmethod
    def is_authenticated(self, token_store) -> bool:
        """Check if valid (or refreshable) tokens exist."""
        ...