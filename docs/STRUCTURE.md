# Project Structure

mirrormate-flask/
├── app.py                          # Flask entry point
├── config.yaml                     # All service endpoints (the "lego blocks" config)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── providers/                      # ← The abstraction layer
│   ├── __init__.py
│   ├── base.py                     # Abstract base classes (STT, TTS, LLM)
│   ├── factory.py                  # Registry + factory pattern
│   ├── stt/
│   │   ├── __init__.py
│   │   ├── faster_whisper.py
│   │   └── openai_stt.py
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── piper.py
│   │   └── openai_tts.py
│   └── llm/
│       ├── __init__.py
│       ├── ollama.py
│       └── openai_llm.py
├── services/
│   ├── __init__.py
│   └── chat.py                     # Orchestrates STT → LLM → TTS pipeline
├── piper-server/                   # Thin HTTP wrapper for Piper TTS
│   ├── server.py
│   ├── requirements.txt
│   └── Dockerfile
├── templates/
│   └── mirror.html
└── static/
    ├── css/
    │   └── mirror.css
    └── js/
        ├── audio.js                # Mic capture + Web Audio API analyser
        ├── face.js                 # SVG face state machine
        └── app.js                  # Wires everything together
