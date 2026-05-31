"""
TokenStore — encrypted OAuth token persistence in SQLite.

Tokens are encrypted at rest using Fernet symmetric encryption
derived from the Flask secret key. No plaintext tokens on disk.
"""
import json
import hashlib
import base64
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger(__name__)


class TokenStore:
    def __init__(self, db_path: str, secret_key: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Derive a Fernet key from the Flask secret key
        key_bytes = hashlib.sha256(secret_key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

        self._init_db()
        log.info("TokenStore ready — db: %s", db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    provider   TEXT PRIMARY KEY,
                    token_data BLOB NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def save_token(self, provider: str, token_data: dict):
        """Encrypt and store token data for a provider."""
        plaintext = json.dumps(token_data).encode("utf-8")
        encrypted = self._fernet.encrypt(plaintext)
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tokens (provider, token_data, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(provider) DO UPDATE SET token_data=?, updated_at=?",
                (provider, encrypted, now, encrypted, now),
            )
        log.info("Saved token for provider: %s", provider)

    def get_token(self, provider: str) -> dict | None:
        """Retrieve and decrypt token data for a provider."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT token_data FROM tokens WHERE provider = ?",
                (provider,),
            ).fetchone()

        if not row:
            return None

        try:
            plaintext = self._fernet.decrypt(row["token_data"])
            return json.loads(plaintext)
        except (InvalidToken, json.JSONDecodeError) as e:
            log.error("Failed to decrypt token for %s: %s", provider, e)
            return None

    def delete_token(self, provider: str):
        """Remove stored token for a provider."""
        with self._connect() as conn:
            conn.execute("DELETE FROM tokens WHERE provider = ?", (provider,))
        log.info("Deleted token for provider: %s", provider)

    def has_token(self, provider: str) -> bool:
        """Check if a token exists for a provider."""
        return self.get_token(provider) is not None
