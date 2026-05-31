"""
MemoryStore — SQLite-backed conversation persistence.

Handles sessions and messages with a configurable context window
for LLM token management.
"""
import sqlite3
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self, db_path: str = "data/mirror.db", context_window: int = 20):
        self.db_path = db_path
        self.context_window = context_window

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        log.info("MemoryStore ready — db: %s, context_window: %d",
                 db_path, context_window)

    # ── Schema ───────────────────────────────────────

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id         TEXT PRIMARY KEY,
                    title      TEXT NOT NULL DEFAULT 'New conversation',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role       TEXT NOT NULL,
                    content    TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, created_at);
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ── Sessions ─────────────────────────────────────

    def create_session(self) -> str:
        """Create a new conversation session, return its ID."""
        sid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (sid, "New conversation", now, now),
            )
        log.info("Created session: %s", sid)
        return sid

    def get_session(self, session_id: str) -> dict | None:
        """Get session metadata."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_sessions(self, limit: int = 50) -> list[dict]:
        """List recent sessions, newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT s.*, COUNT(m.id) as message_count "
                "FROM sessions s "
                "LEFT JOIN messages m ON m.session_id = s.id "
                "GROUP BY s.id "
                "ORDER BY s.updated_at DESC "
                "LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: str):
        """Delete a session and all its messages."""
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        log.info("Deleted session: %s", session_id)

    def _update_session_title(self, session_id: str, first_message: str):
        """Auto-title the session from the first user message."""
        title = first_message[:80].strip()
        if len(first_message) > 80:
            title += "…"
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? "
                "WHERE id = ? AND title = 'New conversation'",
                (title, now, session_id),
            )

    def _touch_session(self, session_id: str):
        """Update the session's updated_at timestamp."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )

    # ── Messages ─────────────────────────────────────

    def add_message(self, session_id: str, role: str, content: str):
        """Store a message and update session metadata."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) "
                "VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )

        # Auto-title on first user message
        if role == "user":
            self._update_session_title(session_id, content)

        self._touch_session(session_id)

    def get_messages(self, session_id: str) -> list[dict]:
        """Get ALL messages for a session (for display)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM messages "
                "WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_context(self, session_id: str) -> list[dict]:
        """
        Get the most recent messages for LLM context.
        Returns at most `context_window` messages to keep token usage sane.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages "
                "WHERE session_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (session_id, self.context_window),
            ).fetchall()
        # Reverse to chronological order
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def clear_session_messages(self, session_id: str):
        """Delete all messages in a session but keep the session."""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM messages WHERE session_id = ?", (session_id,)
            )
            conn.execute(
                "UPDATE sessions SET title = 'New conversation', "
                "updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), session_id),
            )
        log.info("Cleared messages for session: %s", session_id)

    # ── Stats ────────────────────────────────────────

    def stats(self) -> dict:
        """Quick DB stats."""
        with self._connect() as conn:
            sessions = conn.execute(
                "SELECT COUNT(*) as c FROM sessions"
            ).fetchone()["c"]
            messages = conn.execute(
                "SELECT COUNT(*) as c FROM messages"
            ).fetchone()["c"]
        return {"sessions": sessions, "messages": messages}
