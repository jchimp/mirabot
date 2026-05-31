# Version History

## 1.2.0 - 2026-05-01
    - Changed name to: Mira Bot (mirabot). 
        Update README, config.yaml, docker-compose, etc. 
        Renamed mirror.html -> index.html, mirror.css -> style.css.
    - Adding query Outlook/Google calendar
        - Adding OAuth 2.0 Authentication with Device Code login URL for Google and Microsoft accounts.
        - We will store the OAuth token in the SQLite DB.
        - Adding automatic token refresh 

        Updated Structure:
        mirrormate-flask/
        ├── providers/
        │   ├── base.py                    ← add CalendarProvider ABC
        │   ├── factory.py                 ← register calendar providers
        │   └── calendar/
        │       ├── __init__.py            ← NEW
        │       ├── google_cal.py          ← NEW: Google Calendar
        │       └── outlook.py             ← NEW: stub for v1.3
        ├── services/
        │   ├── token_store.py             ← NEW: encrypted token storage
        │   ├── calendar_context.py        ← NEW: fetch, cache, format events
        │   └── chat.py                    ← UPDATED: inject calendar context
        ├── app.py                         ← UPDATED: init calendar, CLI commands
        ├── config.yaml                    ← UPDATED: calendar section
        ├── requirements.txt               ← UPDATED: google + crypto libs
        └── docker-compose.yml             ← UPDATED: expose auth port

    - Added new config section for calendar provider
    - Added docker-compose for the the additional port for the auth call back from Google/MS
    - Updated requirements.txt

TODO: Load existing chats into 'memory' and/or suppliment with RAG...see TODO


# 1.1.1 - 2026-05-01
    - Add CSS theme switch between "dark mirror" mode and "dark interactive UI" mode
    - Adding in JSON export for the memories/converstations. This is kind of a "breaking" change, but eh - it's a pet project.
    

# 1.1.0 - 2026-05-01
    - Added converstation history with SQLite DB. Created services/memory.py to act as the memory storage & retrevial object.
        ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
        │ Flask App   │────▶│ MemoryStore  │───▶│ SQLite DB    │
        │ (app.py)    │     │ (memory.py)  │     │ (mirror.db)  │
        └─────────────┘     └──────────────┘     └──────────────┘

        Tables:
        sessions  ── id, title, created_at, updated_at
        messages  ── id, session_id (FK), role, content, created_at

        - Persistent conversations — survive restarts
        - Multiple sessions — sidebar to switch between them
        - Context window — configurable max messages sent to the LLM (keeps token usage sane)
        - Auto-title — first user message becomes the session title
        - Clean UI — slide-out history panel, stays minimal
    - Added history sidebar to mirror.html
    - Updated app.js - history UI logic
    - Updated app.py - use memory object instead of [dict]


# 1.0.0 - 2026-04-30
    - Initial version. Writen with help from Copilot.
    - No converstation history or embeddings
    - All containers for each server can run local.
    - Created with inspiration from this project: https://github.com/orangekame3/mirrormate


