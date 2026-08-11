"""Persistent local memory for ORBIT.

Backed by SQLite (stdlib) so it works with zero extra dependencies and is
fully local-first. Stores: preferences, known applications, vocabulary,
workflows (skill references), corrections, and a success/failure action log.

SECRETS ARE NEVER STORED HERE. Any key/value whose name looks like a secret
is rejected — use environment variables / OS credential storage instead.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

_SECRET_HINTS = ("password", "passwd", "secret", "api_key", "apikey", "token", "credential", "private_key")


class SecretRejected(Exception):
    pass


def _looks_like_secret(key: str) -> bool:
    lowered = key.lower()
    return any(hint in lowered for hint in _SECRET_HINTS)


SCHEMA = """
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    name TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL,
    aliases TEXT NOT NULL DEFAULT '[]',
    category TEXT DEFAULT '',
    created_at REAL NOT NULL,
    UNIQUE(term)
);

CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    approved_for_training INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS workflows (
    name TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    command TEXT NOT NULL,
    actions TEXT NOT NULL DEFAULT '[]',
    result TEXT DEFAULT '',
    status TEXT NOT NULL
);
"""


@dataclass
class ActivityRecord:
    id: int
    timestamp: float
    command: str
    actions: list
    result: str
    status: str


class MemoryStore:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        finally:
            cur.close()

    def close(self) -> None:
        self._conn.close()

    # ---- preferences ----
    def set_preference(self, key: str, value: Any) -> None:
        if _looks_like_secret(key):
            raise SecretRejected(
                f"Refusing to store '{key}' in memory — it looks like a secret. "
                "Use environment variables or OS credential storage instead."
            )
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO preferences(key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, json.dumps(value), time.time()),
            )

    def get_preference(self, key: str, default: Any = None) -> Any:
        with self._cursor() as cur:
            row = cur.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def list_preferences(self) -> dict:
        with self._cursor() as cur:
            rows = cur.execute("SELECT key, value FROM preferences").fetchall()
        return {k: json.loads(v) for k, v in rows}

    def delete_preference(self, key: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM preferences WHERE key=?", (key,))

    # ---- applications ----
    def upsert_application(self, name: str, data: dict) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO applications(name, data, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
                (name, json.dumps(data), time.time()),
            )

    def get_application(self, name: str) -> Optional[dict]:
        with self._cursor() as cur:
            row = cur.execute("SELECT data FROM applications WHERE name=?", (name,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_applications(self) -> list[dict]:
        with self._cursor() as cur:
            rows = cur.execute("SELECT data FROM applications").fetchall()
        return [json.loads(r[0]) for r in rows]

    def delete_application(self, name: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM applications WHERE name=?", (name,))

    # ---- vocabulary ----
    def add_vocabulary(self, term: str, aliases: Optional[list[str]] = None, category: str = "") -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO vocabulary(term, aliases, category, created_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(term) DO UPDATE SET aliases=excluded.aliases, category=excluded.category",
                (term, json.dumps(aliases or []), category, time.time()),
            )

    def list_vocabulary(self) -> list[dict]:
        with self._cursor() as cur:
            rows = cur.execute("SELECT term, aliases, category FROM vocabulary").fetchall()
        return [{"term": t, "aliases": json.loads(a), "category": c} for t, a, c in rows]

    def delete_vocabulary(self, term: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM vocabulary WHERE term=?", (term,))

    # ---- corrections (raw vs interpreted transcript learning data) ----
    def add_correction(self, raw_text: str, corrected_text: str, approved_for_training: bool = False) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO corrections(raw_text, corrected_text, approved_for_training, created_at) "
                "VALUES (?, ?, ?, ?)",
                (raw_text, corrected_text, int(approved_for_training), time.time()),
            )
            return cur.lastrowid

    def list_corrections(self, approved_only: bool = False) -> list[dict]:
        query = "SELECT id, raw_text, corrected_text, approved_for_training, created_at FROM corrections"
        if approved_only:
            query += " WHERE approved_for_training=1"
        with self._cursor() as cur:
            rows = cur.execute(query).fetchall()
        return [
            {"id": r[0], "raw_text": r[1], "corrected_text": r[2], "approved_for_training": bool(r[3]), "created_at": r[4]}
            for r in rows
        ]

    def delete_correction(self, correction_id: int) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM corrections WHERE id=?", (correction_id,))

    # ---- workflows / skills references ----
    def upsert_workflow(self, name: str, data: dict) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO workflows(name, data, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
                (name, json.dumps(data), time.time()),
            )

    def get_workflow(self, name: str) -> Optional[dict]:
        with self._cursor() as cur:
            row = cur.execute("SELECT data FROM workflows WHERE name=?", (name,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_workflows(self) -> list[dict]:
        with self._cursor() as cur:
            rows = cur.execute("SELECT data FROM workflows").fetchall()
        return [json.loads(r[0]) for r in rows]

    def delete_workflow(self, name: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM workflows WHERE name=?", (name,))

    # ---- activity log ----
    def log_activity(self, command: str, actions: list[str], result: str, status: str) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO activity_log(timestamp, command, actions, result, status) VALUES (?, ?, ?, ?, ?)",
                (time.time(), command, json.dumps(actions), result, status),
            )
            return cur.lastrowid

    def list_activity(self, limit: int = 50) -> list[ActivityRecord]:
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT id, timestamp, command, actions, result, status FROM activity_log "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            ActivityRecord(id=r[0], timestamp=r[1], command=r[2], actions=json.loads(r[3]), result=r[4], status=r[5])
            for r in rows
        ]

    def delete_activity(self, activity_id: int) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM activity_log WHERE id=?", (activity_id,))
