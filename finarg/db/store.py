"""SQLite store for transaction logging."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class TransactionLog:
    """Logs all financial operations for audit trail."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                args TEXT NOT NULL,
                result TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 1
            )"""
        )
        self._conn.commit()

    def log(self, tool_name: str, args: dict, result: str, success: bool = True) -> None:
        self._conn.execute(
            "INSERT INTO transactions (timestamp, tool_name, args, result, success) VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                tool_name,
                json.dumps(args),
                result,
                1 if success else 0,
            ),
        )
        self._conn.commit()

    def recent(self, limit: int = 20) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT timestamp, tool_name, args, result, success FROM transactions ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [
            {
                "timestamp": row[0],
                "tool_name": row[1],
                "args": json.loads(row[2]),
                "result": row[3],
                "success": bool(row[4]),
            }
            for row in cursor.fetchall()
        ]

    def close(self) -> None:
        self._conn.close()
