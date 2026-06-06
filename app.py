"""
Mira Bot — main application.
"""
import os
import json
import logging

import yaml
import click
from datetime import datetime, timezone
from flask import Flask, render_template, request, session, jsonify
from flask import Response as FlaskResponse

from providers import create_providers
from services.chat import ChatService
from services.memory import MemoryStore
from services.token_store import TokenStore
from services.calendar_context import CalendarContext

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# ── Load config ──────────────────────────────────────────
CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

# ── Flask app ────────────────────────────────────────────
app = Flask(__name__)

_secret = os.environ.get("FLASK_SECRET_KEY")
if not _secret:
    raise RuntimeError("FLASK_SECRET_KEY environment variable is required")
app.secret_key = _secret
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

# ── Providers ────────────────────────────────────────────
providers = create_providers(config)

# ── Memory ───────────────────────────────────────────────
memory_config = config.get("memory", {})
memory = MemoryStore(
    db_path=memory_config.get("db_path", "data/mirabot.db"),
    context_window=memory_config.get("context_window", 20),
)

# ── Token Store ──────────────────────────────────────────
token_store = TokenStore(
    db_path=memory_config.get("db_path", "data/mirabot.db"),
    secret_key=app.secret_key,
)

# ── Calendar Context (optional) ──────────────────────────
cal_config = config.get("calendar", {})
calendar_context = None

if providers.get("calendar"):
    calendar_context = CalendarContext(
        provider=providers["calendar"],
        token_store=token_store,
        config=cal_config,
    )
    log.info("Calendar integration enabled: %s (cache TTL: %dm)",
             cal_config.get("provider"), cal_config.get("cache_ttl_minutes", 5))
else:
    log.info("Calendar integration disabled")

# ── Chat Service ─────────────────────────────────────────
assistant_config = config.get("assistant", {})
chat_service = ChatService(
    stt=providers["stt"],
    tts=providers["tts"],
    llm=providers["llm"],
    system_prompt=assistant_config.get("system_prompt", ""),
    calendar_context=calendar_context,
)


def _get_or_create_session() -> str:
    sid = session.get("sid")
    if sid and memory.get_session(sid):
        return sid
    sid = memory.create_session()
    session["sid"] = sid
    return sid


# ═══════════════════════════════════════════════════════════
#  Routes
# ═══════════════════════════════════════════════════════════

@app.route("/")
def index():
    assistant = config.get("assistant", {})
    name = assistant.get("name", "Mirror")
    default_theme = assistant.get("default_theme", "mirror")
    default_face = assistant.get("default_face", "face")
    transform_volume = assistant.get("transform_volume", 0.5)
    return render_template("index.html",
                           assistant_name=name,
                           default_theme=default_theme,
                           default_face=default_face,
                           transform_volume=transform_volume)


@app.route("/api/converse", methods=["POST"])
def converse():
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No audio file provided"}), 400

    audio_bytes = audio_file.read()
    mime_type = audio_file.content_type or "audio/webm"
    sid = _get_or_create_session()
    history = memory.get_context(sid)

    try:
        result = chat_service.converse(audio_bytes, history, mime_type)
        if result["user_text"]:
            memory.add_message(sid, "user", result["user_text"])
        memory.add_message(sid, "assistant", result["response_text"])
        result["session_id"] = sid
        return jsonify(result)
    except Exception as e:
        log.exception("Pipeline error")
        return jsonify({"error": str(e)}), 500


@app.route("/api/converse/stream", methods=["POST"])
def converse_stream():
    """
    SSE streaming pipeline: audio → transcript → sentence chunks with audio → done.

    Event types:
      data: {"type": "transcript", "text": "..."}
      data: {"type": "chunk", "text": "...", "audio": "<base64 WAV>"}
      data: {"type": "done", "session_id": "...", "response_text": "..."}
      data: {"type": "error", "message": "..."}
    """
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No audio file provided"}), 400

    audio_bytes = audio_file.read()
    mime_type = audio_file.content_type or "audio/webm"
    sid = _get_or_create_session()
    history = memory.get_context(sid)

    def generate():
        for event in chat_service.converse_stream(audio_bytes, history, mime_type):
            if event["type"] == "done":
                if event.get("user_text"):
                    memory.add_message(sid, "user", event["user_text"])
                if event.get("response_text"):
                    memory.add_message(sid, "assistant", event["response_text"])
                event["session_id"] = sid
            yield f"data: {json.dumps(event)}\n\n"

    return FlaskResponse(generate(), mimetype="text/event-stream",
                         headers={"X-Accel-Buffering": "no",
                                  "Cache-Control": "no-cache"})


# ── Session Management ───────────────────────────────────

@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    sessions = memory.list_sessions()
    current = session.get("sid")
    return jsonify({"sessions": sessions, "current": current})


@app.route("/api/sessions", methods=["POST"])
def new_session():
    sid = memory.create_session()
    session["sid"] = sid
    return jsonify({"session_id": sid})


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session_messages(session_id):
    s = memory.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    messages = memory.get_messages(session_id)
    return jsonify({"session": s, "messages": messages})


@app.route("/api/sessions/<session_id>/switch", methods=["POST"])
def switch_session(session_id):
    s = memory.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    session["sid"] = session_id
    messages = memory.get_messages(session_id)
    return jsonify({"session": s, "messages": messages})


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    memory.delete_session(session_id)
    if session.get("sid") == session_id:
        new_sid = memory.create_session()
        session["sid"] = new_sid
        return jsonify({"status": "ok", "new_session_id": new_sid})
    return jsonify({"status": "ok"})


@app.route("/api/sessions/<session_id>/export")
def export_session(session_id):
    s = memory.get_session(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    messages = memory.get_messages(session_id)
    export = {
        "session": {
            "id": s["id"], "title": s["title"],
            "created_at": s["created_at"], "updated_at": s["updated_at"],
        },
        "messages": messages,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "message_count": len(messages),
    }
    filename = f"mirror-{s['title'][:40].replace(' ', '-')}.json"
    return FlaskResponse(
        json.dumps(export, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/api/sessions/import", methods=["POST"])
def import_session():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400
    try:
        data = json.loads(file.read())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return jsonify({"error": "Invalid JSON file"}), 400
    if "messages" not in data or not isinstance(data["messages"], list):
        return jsonify({"error": "Invalid format — missing 'messages' array"}), 400
    for i, msg in enumerate(data["messages"]):
        if "role" not in msg or "content" not in msg:
            return jsonify({"error": f"Message {i} missing 'role' or 'content'"}), 400

    sid = memory.create_session()
    original = data.get("session", {})
    title = original.get("title", "Imported conversation")
    memory.rename_session(sid, title)
    count = 0
    for msg in data["messages"]:
        if msg["role"] not in ("user", "assistant"):
            continue
        memory.add_message(sid, msg["role"], msg["content"])
        count += 1
    session["sid"] = sid
    return jsonify({"session_id": sid, "title": title, "message_count": count})


@app.route("/api/clear", methods=["POST"])
def clear():
    sid = _get_or_create_session()
    memory.clear_session_messages(sid)
    return jsonify({"status": "ok"})


@app.route("/api/health")
def health():
    status = {}
    for name, provider in providers.items():
        if provider is None:
            status[name] = "disabled"
        elif name == "calendar":
            # Calendar health = is authenticated
            try:
                authed = provider.is_authenticated(token_store)
                status[name] = "ok" if authed else "not authenticated"
            except Exception:
                status[name] = "error"
        else:
            status[name] = "ok" if provider.health() else "unreachable"

    overall = "ok" if all(v in ("ok", "disabled", "not authenticated") for v in status.values()) else "degraded"
    return jsonify({"status": overall, "providers": status, "memory": memory.stats()})


# ═══════════════════════════════════════════════════════════
#  CLI Commands
# ═══════════════════════════════════════════════════════════

@app.cli.command("calendar-setup")
@click.argument("provider", default="")
def calendar_setup(provider):
    """Authenticate with your calendar provider.

    Usage:
        flask calendar-setup          (uses provider from config.yaml)
        flask calendar-setup google
        flask calendar-setup outlook
    """
    cal_cfg = config.get("calendar", {})
    provider = provider or cal_cfg.get("provider", "")

    if not provider or provider.lower() == "none":
        click.echo("\n❌ No calendar provider configured.")
        click.echo("   Set 'calendar.provider' in config.yaml to 'google' or 'outlook'.\n")
        return

    cal_provider = providers.get("calendar")
    if cal_provider is None:
        click.echo(f"\n❌ Calendar provider '{provider}' is not loaded.")
        click.echo("   Check your config.yaml.\n")
        return

    click.echo(f"\nSetting up calendar: {provider}")
    click.echo("-" * 40)

    try:
        success = cal_provider.authenticate_interactive(token_store)
        if success:
            # Quick test — fetch today's events
            from datetime import timedelta
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(cal_cfg.get("timezone", "America/Denver"))
            now = datetime.now(tz)
            end = now + timedelta(days=1)

            events = cal_provider.get_events(now, end, token_store)
            click.echo(f"\n📅 Found {len(events)} events today:")
            for e in events[:5]:
                click.echo(f"   - {e['summary']}")
            if len(events) > 5:
                click.echo(f"   ... and {len(events) - 5} more")
            if not events:
                click.echo("   (no events today)")
            click.echo()
        else:
            click.echo("\n❌ Authentication was not completed.\n")
    except Exception as e:
        click.echo(f"\n❌ Setup failed: {e}\n")
        log.exception("Calendar setup failed")


@app.cli.command("calendar-status")
def calendar_status():
    """Check calendar integration status."""
    cal_cfg = config.get("calendar", {})
    provider_name = cal_cfg.get("provider", "none")

    click.echo(f"\nCalendar provider:  {provider_name}")
    click.echo(f"Context mode:       {cal_cfg.get('context_mode', 'none')}")
    click.echo(f"Lookahead:          {cal_cfg.get('lookahead_days', 3)} days")
    click.echo(f"Cache TTL:          {cal_cfg.get('cache_ttl_minutes', 5)} minutes")
    click.echo(f"Timezone:           {cal_cfg.get('timezone', 'not set')}")

    if providers.get("calendar"):
        authed = providers["calendar"].is_authenticated(token_store)
        click.echo(f"Authenticated:      {'✅ yes' if authed else '❌ no'}")

        if authed and calendar_context:
            click.echo("\nFetching calendar preview...")
            ctx = calendar_context.get_context_string()
            if ctx:
                click.echo(ctx)
            else:
                click.echo("(no events in lookahead window)")
    else:
        click.echo("Authenticated:      N/A (disabled)")

    click.echo()


@app.cli.command("calendar-logout")
@click.argument("provider", default="")
def calendar_logout(provider):
    """Remove stored calendar tokens."""
    provider = provider or config.get("calendar", {}).get("provider", "")
    if not provider:
        click.echo("\n❌ No provider specified.\n")
        return

    token_store.delete_token(provider)
    if calendar_context:
        calendar_context.invalidate_cache()
    click.echo(f"\n✅ Tokens removed for '{provider}'.\n")


# ── Dev server ───────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
