# Mira Bot

A voice-powered AI assistant with a real-time animated face, built on swappable "lego block" providers. Talk to it, and it listens, thinks, and speaks back — with calendar awareness, conversation memory, and a HAL 9000 mode.

```
🎤 Mic → 🗣️ faster-whisper (STT) → 🧠 Ollama (LLM) → 🔊 Piper (TTS) → 🔈 Speaker
```

---

## Features

- **Voice conversation** — push-to-talk with real-time speech-to-text and text-to-speech
- **Animated face** — SVG face with blinking eyes, mouth sync driven by audio amplitude
- **HAL 9000 mode** — swap the face for an analog red eye that pulses when speaking
- **Calendar integration** — Google Calendar (Outlook coming soon) context injected into every conversation
- **Conversation memory** — SQLite-backed persistent history across sessions
- **Theme system** — dark mirror (pure black) and slate (dark grey) themes with smooth transitions
- **Import/export** — save and load conversations as JSON
- **Provider abstraction** — swap any AI service by changing one line in `config.yaml`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (UI)                            │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Audio.js │  │  Face.js  │  │  App.js  │  │  mirror.css   │  │
│  │ (mic +   │  │ (SVG face │  │ (wires   │  │ (themes +     │  │
│  │ playback)│  │  + HAL)   │  │ it all)  │  │  animations)  │  │
│  └──────────┘  └───────────┘  └──────────┘  └───────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ POST /api/converse (audio blob)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Flask App (app.py)                           │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐     │
│  │ ChatService │  │ MemoryStore │  │ CalendarContext       │     │
│  │ (pipeline)  │  │ (SQLite)    │  │ (fetch + cache + fmt) │     │
│  └──────┬──────┘  └─────────────┘  └──────────┬───────────┘     │
│         │                                      │                 │
│  ┌──────▼──────────────────────────────────────▼───────────┐     │
│  │              Provider Abstraction Layer                  │     │
│  │  ┌─────┐  ┌─────┐  ┌─────┐  ┌──────────┐              │     │
│  │  │ STT │  │ TTS │  │ LLM │  │ Calendar │              │     │
│  │  └──┬──┘  └──┬──┘  └──┬──┘  └────┬─────┘              │     │
│  └─────┼────────┼────────┼──────────┼──────────────────────┘     │
└────────┼────────┼────────┼──────────┼────────────────────────────┘
         │        │        │          │
         ▼        ▼        ▼          ▼
   ┌──────────┐ ┌─────┐ ┌──────┐ ┌──────────────┐
   │ faster-  │ │Piper│ │Ollama│ │Google Calendar│
   │ whisper  │ │ TTS │ │      │ │     API       │
   └──────────┘ └─────┘ └──────┘ └──────────────┘
```

Every provider implements an abstract base class. Swap any service by changing `provider` in `config.yaml` — no code changes required.

---

## Dependencies & Projects Used

| Component                | Project                                                                                                                                       | Role                                        |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **Speech-to-Text**       | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) via [whisper-asr-webservice](https://github.com/ahmetoner/whisper-asr-webservice) | Converts speech to text                     |
| **Text-to-Speech**       | [Piper TTS](https://github.com/rhasspy/piper)                                                                                                 | Converts text to natural speech             |
| **Large Language Model** | [Ollama](https://ollama.com/)                                                                                                                 | Local LLM inference (llama3, mistral, etc.) |
| **Web Framework**        | [Flask](https://flask.palletsprojects.com/)                                                                                                   | Backend API and web UI                      |
| **Calendar**             | [Google Calendar API](https://developers.google.com/calendar)                                                                                 | Read-only calendar access                   |
| **Auth**                 | [google-auth-oauthlib](https://github.com/googleapis/google-auth-library-python-oauthlib)                                                     | OAuth 2.0 for Google                        |
| **Token Encryption**     | [cryptography (Fernet)](https://cryptography.io/)                                                                                             | Encrypt OAuth tokens at rest                |
| **Database**             | SQLite                                                                                                                                        | Conversation memory + token storage         |
| **Containerization**     | Docker + Docker Compose                                                                                                                       | Service orchestration                       |

### Python Dependencies

```
flask>=3.0
gunicorn>=22.0
pyyaml>=6.0
requests>=2.31
google-auth>=2.29
google-auth-oauthlib>=1.2
google-api-python-client>=2.130
cryptography>=42.0
```

---

## Prerequisites

- **Docker** and **Docker Compose** (Docker Desktop on Windows/Mac, or Docker Engine on Linux)
- **Ollama** installed (either locally or in Docker)
- A microphone and speakers/headphones
- A modern browser (Chrome recommended)

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/jchimp/mirabot.git
cd mirabot
```

### 2. Download Piper voice model

```bash
mkdir -p piper-models
cd piper-models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
cd ..
```

### 3. Configure

Copy and edit the config file:

```bash
cp config.yaml.example config.yaml
```

At minimum, set your Ollama URL (see [Ollama Setup](#ollama-setup) below).

### 4. Set your secret key

```bash
# Linux/Mac
export FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Windows PowerShell
$env:FLASK_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Start everything

```bash
docker compose up -d --build
```

### 6. Pull your LLM model (if using Ollama in Docker)

```bash
docker exec mirror-ollama ollama pull llama3
```

### 7. Open in browser

```
http://localhost:5000
```

---

## Ollama Setup

You have two options for running Ollama:

### Option A: Ollama in Docker (fully containerized)

Uncomment the `ollama` service in `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: mirror-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # Uncomment for GPU passthrough:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]
    restart: unless-stopped
```

Set `config.yaml`:

```yaml
llm:
  provider: "ollama"
  url: "http://ollama:11434"     # Docker service name
  model: "llama3"
```

Then start and pull:

```bash
docker compose up -d
docker exec mirror-ollama ollama pull llama3
```

> **Note:** Running Ollama in Docker without GPU passthrough will be CPU-only
> and significantly slower. For best performance, use Option B with GPU access.

### Option B: Ollama on the host machine (or another host)

Install Ollama normally, then point MiraBot to it.

**Same machine as Docker (Windows/Mac — Docker Desktop):**

```yaml
llm:
  provider: "ollama"
  url: "http://host.docker.internal:11434"
  model: "llama3"
```

> `host.docker.internal` is a special Docker hostname that resolves to the host
> machine. Docker Desktop (Windows/Mac) supports it out of the box.

**Same machine as Docker (Linux):**

```yaml
llm:
  provider: "ollama"
  url: "http://host.docker.internal:11434"
  model: "llama3"
```

Add this to the `mirror` service in `docker-compose.yml`:

```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

**Different machine on your network:**

```yaml
llm:
  provider: "ollama"
  url: "http://192.168.1.100:11434"    # IP of the Ollama host
  model: "llama3"
```

> **Important:** Ollama must listen on all interfaces, not just localhost.
> Set the environment variable `OLLAMA_HOST=0.0.0.0` and restart Ollama.
>
> The model name in `config.yaml` must match exactly what `ollama list` shows.

---

## Configuration Reference

All configuration lives in `config.yaml`:

```yaml
# ── Assistant ────────────────────────────────────────────
assistant:
  name: "Mirror"
  system_prompt: >
    You are Mirror, a friendly and concise AI assistant...
  default_theme: "mirror"       # "mirror" (pure black) or "slate" (dark grey)
  default_face: "face"          # "face" (eyes + mouth) or "hal" (HAL 9000)

# ── Speech-to-Text ───────────────────────────────────────
# Providers: faster_whisper | openai
stt:
  provider: "faster_whisper"
  url: "http://whisper-server:9000"
  model: "base"                 # tiny, base, small, medium, large-v3

# ── Text-to-Speech ───────────────────────────────────────
# Providers: piper | openai
tts:
  provider: "piper"
  url: "http://piper-server:5000"
  voice: "en_US-lessac-medium"

# ── Large Language Model ─────────────────────────────────
# Providers: ollama | openai
llm:
  provider: "ollama"
  url: "http://host.docker.internal:11434"
  model: "llama3"

# ── Conversation Memory ─────────────────────────────────
memory:
  db_path: "/data/mirror.db"
  context_window: 20            # max messages sent to LLM per turn

# ── Calendar Integration ────────────────────────────────
# Providers: google | outlook (coming soon) | none
calendar:
  provider: "google"
  client_id: "your-client-id.apps.googleusercontent.com"
  client_secret: "GOCSPX-your-secret"
  scopes:
    - "https://www.googleapis.com/auth/calendar.readonly"
  lookahead_days: 3             # days of events to fetch
  cache_ttl_minutes: 5          # how often to refresh calendar data
  timezone: "America/Denver"
  context_mode: "inject"        # "inject" into system prompt or "none"
```

---

## Calendar Setup

MiraBot can read your Google Calendar so the LLM knows your schedule. Calendar access is **read-only** — MiraBot never creates, modifies, or deletes events. OAuth tokens are encrypted at rest.

### Google Calendar Setup

#### Step 1: Create a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
3. Name it (e.g., "MiraBot") → **Create**

#### Step 2: Enable the Calendar API

1. Go to **APIs & Services** → **Library**
2. Search for **"Google Calendar API"**
3. Click it → **Enable**

#### Step 3: Configure the OAuth consent screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** → **Create**
3. Fill in:
   - App name: `MiraBot`
   - User support email: your email
   - Developer contact: your email
4. Click **Save and Continue** through the remaining steps
5. Go to **Test users** → **Add Users** → add your Google email
6. **Publish** (or leave in testing mode — either works for personal use)

#### Step 4: Create OAuth credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `MiraBot Calendar`
5. Click **Create**
6. Copy the **Client ID** and **Client Secret**

#### Step 5: Add credentials to config.yaml

```yaml
calendar:
  provider: "google"
  client_id: "123456789-abc123def456.apps.googleusercontent.com"
  client_secret: "GOCSPX-YourSecretHere"
  scopes:
    - "https://www.googleapis.com/auth/calendar.readonly"
  lookahead_days: 3
  cache_ttl_minutes: 5
  timezone: "America/Denver"
  context_mode: "inject"
```

#### Step 6: Expose the OAuth callback port

The OAuth flow requires port `8090` to be reachable from your browser. It is commented out in `docker-compose.yml` by default. Uncomment it before running setup:

```yaml
# docker-compose.yml — mirabot service
ports:
  - "5000:5000"
  - "8090:8090"   # ← uncomment this line
```

Alternatively, use the included override file so you don't have to edit the main compose file:

```bash
docker compose -f docker-compose.yml -f docker-compose.calendar-setup.yml up -d
```

#### Step 7: Rebuild and authenticate

```bash
docker compose build --no-cache mirabot
docker compose up -d mirabot
docker exec -it mirabot flask calendar-setup
```

A URL will be printed. Open it in your browser, sign in with your Google account, and authorize access. The token is captured automatically via the local callback on port 8090.

```
============================================================
  Google Calendar — Authorization
============================================================

Please visit this URL to authorize this application:
https://accounts.google.com/o/oauth2/auth?client_id=...

✅ Google Calendar authorized successfully!
   Tokens stored and encrypted.

📅 Found 3 events today:
   - Daily Standup
   - 1:1 with Andrea
   - IT Infrastructure Review
```

#### Step 8: Close the callback port

Once authorized, comment port `8090` back out (or stop using the override) and restart:

```bash
docker compose up -d
```

Port 8090 is not needed again unless you run `calendar-setup` again (e.g. after `calendar-logout`).

#### Step 9: Verify

```bash
# Check status and see a calendar preview
docker exec -it mirabot flask calendar-status

# Check the health endpoint
curl http://localhost:5000/api/health
```

Now ask MiraBot:

- *"What's on my calendar today?"*
- *"Am I free at 2pm?"*
- *"What does my week look like?"*

### Calendar CLI Commands

```bash
# Run interactive OAuth flow
docker exec -it mirabot flask calendar-setup

# Check auth status and preview upcoming events
docker exec -it mirabot flask calendar-status

# Remove stored tokens (logout)
docker exec -it mirabot flask calendar-logout
```

> **Note:** Port `8090` is only needed during `flask calendar-setup`. It is commented out
> in `docker-compose.yml` by default — open it for setup, then close it again.

### Outlook.com (Coming in v1.3)

Outlook.com support via Microsoft Graph API and MSAL device code flow is planned.
The provider stub is already in place at `providers/calendar/outlook.py`.

---

## Usage

### Push to Talk

- **Click the mic button** or **press Spacebar** to start recording
- Speak your question
- **Click again** or **press Spacebar** to stop and send

### Theme Toggle

Click the sun/moon icon in the top-right to switch between:

- 🌑 **Mirror** — pure black, minimal, designed for actual smart mirrors
- 🌒 **Slate** — dark grey with subtle card backgrounds and blue accents

### Face Toggle

Click the face icon in the top-right to switch between:

- 😊 **Face** — animated eyes with blinking, pupils that move while thinking, mouth syncs to audio
- 🔴 **HAL** — HAL 9000 analog eye that glows and pulses with the audio amplitude

### Conversation History

- Click **☰** (top-left) to open the sidebar
- Switch between past conversations
- **+** to start a new conversation
- **↓** to import a conversation from JSON
- **↓** on a session to export it as JSON
- **✕** to delete a conversation

### Health Check

```bash
curl http://localhost:5000/api/health
```

```json
{
  "status": "ok",
  "providers": {
    "stt": "ok",
    "tts": "ok",
    "llm": "ok",
    "calendar": "ok"
  },
  "memory": {
    "sessions": 5,
    "messages": 42
  }
}
```

---

## Adding a New Provider

The provider system uses a decorator-based registry. Three steps to add any new service:

### 1. Create the provider class

```python
# providers/tts/elevenlabs.py
import requests
from providers.base import TTSProvider
from providers.factory import register


@register("tts", "elevenlabs")
class ElevenLabsTTS(TTSProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key", "")

    def synthesize(self, text: str) -> bytes:
        resp = requests.post(
            f"{self.url}/v1/text-to-speech/{self.voice}",
            headers={"xi-api-key": self.api_key},
            json={"text": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.content
```

### 2. Register the import in `providers/factory.py`

```python
import providers.tts.elevenlabs  # noqa: F401
```

### 3. Update `config.yaml`

```yaml
tts:
  provider: "elevenlabs"
  url: "https://api.elevenlabs.io"
  voice: "your-voice-id"
  api_key: "sk-..."
```

No other code changes. The factory pattern handles the rest.

---

## Project Structure

```
mirabot/
├── app.py                          # Flask app + routes + CLI commands
├── config.yaml                     # All configuration
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Flask app container
├── docker-compose.yml              # Service orchestration
│
├── providers/                      # Provider abstraction layer
│   ├── base.py                     # Abstract base classes
│   ├── factory.py                  # Registry + factory
│   ├── stt/
│   │   ├── faster_whisper.py       # whisper-asr-webservice client
│   │   └── openai_stt.py           # OpenAI Whisper API client
│   ├── tts/
│   │   ├── piper.py                # Piper TTS client
│   │   └── openai_tts.py           # OpenAI TTS client
│   ├── llm/
│   │   ├── ollama.py               # Ollama /api/chat client
│   │   └── openai_llm.py           # OpenAI-compatible client
│   └── calendar/
│       ├── google_cal.py           # Google Calendar API
│       └── outlook.py              # Outlook.com (stub for v1.3)
│
├── services/
│   ├── chat.py                     # STT → LLM → TTS pipeline orchestration
│   ├── memory.py                   # SQLite conversation persistence
│   ├── token_store.py              # Encrypted OAuth token storage
│   └── calendar_context.py         # Calendar fetch + cache + LLM formatting
│
├── piper-server/                   # Piper TTS HTTP wrapper
│   ├── server.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── piper-models/                   # Voice model files (.onnx)
│
├── templates/
│   └── mirror.html                 # Main UI template
│
└── static/
    ├── css/
    │   └── mirror.css              # Themes + animations
    ├── js/
    │   ├── audio.js                # Mic capture + Web Audio API
    │   ├── face.js                 # SVG face + HAL state machine
    │   └── app.js                  # Wires everything together
    └── audio/
        └── transform.wav           # Face toggle sound effect (optional)
```

---

## Troubleshooting

| Problem                                         | Likely Cause                                   | Fix                                                |
| ----------------------------------------------- | ---------------------------------------------- | -------------------------------------------------- |
| Mic not working                                 | Accessing via IP (not localhost) without HTTPS | Use `localhost` or add HTTPS via Nginx             |
| Empty/0-byte recordings                         | Wrong mic selected or hardware issue           | Check OS audio input settings                      |
| `Connection refused` to whisper/piper           | Services still starting                        | Wait 30–60s on first run, check `docker logs`      |
| `Connection refused` to Ollama                  | Ollama not listening on 0.0.0.0                | Set `OLLAMA_HOST=0.0.0.0` and restart Ollama       |
| `localhost` doesn't reach Ollama from container | Docker networking                              | Use `host.docker.internal` or the machine's IP     |
| Ollama returns 404                              | Model not pulled or name mismatch              | Run `ollama list` and use the exact name in config |
| Calendar `not authenticated`                    | Haven't run setup yet                          | Run `docker exec -it mirabot flask calendar-setup` |
| 500 error on `/api/converse`                    | Provider connection issue                      | Check `docker logs mirabot` for details            |

---

## Roadmap

- [x] Core voice pipeline (STT → LLM → TTS)
- [x] Animated SVG face with audio-driven mouth sync
- [x] HAL 9000 face mode
- [x] Theme system (mirror / slate)
- [x] Conversation memory (SQLite)
- [x] Import / export conversations (JSON)
- [x] Google Calendar integration
- [ ] Outlook.com calendar integration
- [ ] HTTPS via Nginx reverse proxy
- [ ] RAG / document embedding
- [ ] Wake word detection (hands-free)
- [ ] Multi-user support

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with curiosity, Docker, and a lot of debugging. 🪞🤖
