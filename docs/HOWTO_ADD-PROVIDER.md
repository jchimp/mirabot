## How to Add a New Provider
This is the pattern you'll repeat anytime you want to swap in a new service:

```
# providers/tts/elevenlabs.py
import requests
from providers.base import TTSProvider
from providers.factory import register


@register("tts", "elevenlabs")          # ← one decorator
class ElevenLabsTTS(TTSProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")

    def synthesize(self, text: str) -> bytes:
        resp = requests.post(
            f"{self.url}/v1/text-to-speech/{self.voice}",
            headers={"xi-api-key": self.api_key},
            json={"text": text, "model_id": "eleven_monolingual_v1"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.content
```

Then in factory.py, add one import:
```
import providers.tts.elevenlabs  # noqa: F401
```

And in config.yaml:
```
tts:
  provider: "elevenlabs"
  url: "https://api.elevenlabs.io"
  voice: "your-voice-id"
  api_key: "sk-..."
```

Done. No other code changes. True lego blocks.