"""SQLite-backed conversation session storage."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)


class SessionStore:
    """Persistent session store using SQLite with WAL mode.

    Each session holds a list of messages (OpenAI chat-completion format)
    serialised as JSON.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                messages    TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_session(self, session_id: str, messages: list[dict]) -> None:
        """Insert or update a session."""
        now = datetime.now(timezone.utc).isoformat()
        messages_json = json.dumps(messages, ensure_ascii=False)
        self._conn.execute(
            """
            INSERT INTO sessions (id, messages, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                messages   = excluded.messages,
                updated_at = excluded.updated_at
            """,
            (session_id, messages_json, now, now),
        )
        self._conn.commit()

    def load_session(self, session_id: str) -> list[dict] | None:
        """Return the message list for *session_id*, or ``None``."""
        row = self._conn.execute(
            "SELECT messages FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def list_sessions(self) -> list[dict]:
        """Return metadata for every stored session."""
        rows = self._conn.execute(
            "SELECT id, messages, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        results: list[dict] = []
        for sid, messages_json, created_at, updated_at in rows:
            messages = json.loads(messages_json)
            results.append(
                {
                    "id": sid,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "message_count": len(messages),
                }
            )
        return results

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
