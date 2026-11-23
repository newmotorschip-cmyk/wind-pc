"""
Backend SQLite para toda a memória persistente da WIND.
Cria e migra o schema automaticamente ao inicializar.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(os.getenv("WIND_DB_PATH", "data/wind.db"))


def _connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS memory_items (
            id          TEXT PRIMARY KEY,
            created_at  REAL NOT NULL,
            updated_at  REAL NOT NULL,
            mem_type    TEXT NOT NULL,   -- episodic | semantic | procedural
            origin      TEXT NOT NULL,   -- user | wind | tool | system
            title       TEXT NOT NULL DEFAULT '',
            content     TEXT NOT NULL,   -- JSON blob
            tags        TEXT DEFAULT '', -- comma-separated
            confidence  REAL DEFAULT 1.0,
            state       TEXT DEFAULT 'hypothesis',
            session_id  TEXT,
            expires_at  REAL
        );

        CREATE INDEX IF NOT EXISTS idx_mem_type   ON memory_items(mem_type);
        CREATE INDEX IF NOT EXISTS idx_mem_state  ON memory_items(state);
        CREATE INDEX IF NOT EXISTS idx_mem_sess   ON memory_items(session_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
            id UNINDEXED,
            title,
            body,
            tags,
            tokenize = "unicode61"
        );
        """
    )
    conn.commit()


class MemoryStore:
    def __init__(self, path: Path = DB_PATH) -> None:
        self._path = path
        self._conn = _connect(path)
        _migrate(self._conn)

    def put(
        self,
        mem_type: str,
        origin: str,
        content: Any,
        title: str = "",
        tags: list[str] | None = None,
        confidence: float = 1.0,
        state: str = "hypothesis",
        session_id: str | None = None,
        item_id: str | None = None,
    ) -> str:
        import time

        iid = item_id or str(uuid.uuid4())
        now = time.time()
        tags_str = ",".join(tags or [])
        content_json = json.dumps(content, ensure_ascii=False)
        body_text = content if isinstance(content, str) else json.dumps(content)

        self._conn.execute(
            """INSERT OR REPLACE INTO memory_items
               (id, created_at, updated_at, mem_type, origin, title, content, tags, confidence, state, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (iid, now, now, mem_type, origin, title, content_json, tags_str, confidence, state, session_id),
        )
        self._conn.execute(
            "INSERT OR REPLACE INTO memory_fts (id, title, body, tags) VALUES (?, ?, ?, ?)",
            (iid, title, body_text, tags_str),
        )
        self._conn.commit()
        return iid

    @staticmethod
    def _sanitize_fts(query: str) -> str:
        """Mantém apenas palavras (letras/dígitos/underscore) para query FTS5 segura."""
        import re
        words = re.findall(r'[\wÀ-ɏ]+', query)
        words = [w for w in words if w.upper() not in ("AND", "OR", "NOT")]
        return ' '.join(words) if words else "wind"

    def search(self, query: str, limit: int = 5, mem_type: str | None = None) -> list[dict]:
        """Full-text search via FTS5."""
        query = self._sanitize_fts(query)
        if mem_type:
            rows = self._conn.execute(
                """SELECT m.* FROM memory_fts f
                   JOIN memory_items m ON m.id = f.id
                   WHERE f.memory_fts MATCH ? AND m.mem_type = ?
                   ORDER BY rank LIMIT ?""",
                (query, mem_type, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT m.* FROM memory_fts f
                   JOIN memory_items m ON m.id = f.id
                   WHERE f.memory_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (query, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get(self, item_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM memory_items WHERE id = ?", (item_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_by_type(self, mem_type: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM memory_items WHERE mem_type = ? ORDER BY created_at DESC LIMIT ?",
            (mem_type, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_state(self, item_id: str, state: str) -> None:
        import time
        self._conn.execute(
            "UPDATE memory_items SET state = ?, updated_at = ? WHERE id = ?",
            (state, time.time(), item_id),
        )
        self._conn.commit()

    def delete(self, item_id: str) -> None:
        self._conn.execute("DELETE FROM memory_items WHERE id = ?", (item_id,))
        self._conn.execute("DELETE FROM memory_fts WHERE id = ?", (item_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
