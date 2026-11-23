"""
Persistência de ProjectCards em SQLite (mesmo banco wind.db da Fase 1).
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

from .project import ProjectCard, ProjectStatus

DB_PATH = Path(os.getenv("WIND_DB_PATH", "data/wind.db"))


def _get_conn(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            status      TEXT DEFAULT 'active',
            tags        TEXT DEFAULT '[]',
            next_action TEXT DEFAULT '',
            decisions   TEXT DEFAULT '[]',
            files       TEXT DEFAULT '[]',
            notes       TEXT DEFAULT '',
            created_at  REAL,
            updated_at  REAL
        );
        CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
        CREATE INDEX IF NOT EXISTS idx_projects_name   ON projects(name);
    """)
    conn.commit()


class ProjectStore:
    def __init__(self, path: Path = DB_PATH) -> None:
        self._conn = _get_conn(path)
        _migrate(self._conn)

    def save(self, project: ProjectCard) -> None:
        now = time.time()
        project.updated_at = now
        self._conn.execute(
            """INSERT OR REPLACE INTO projects
               (id, name, description, status, tags, next_action, decisions, files, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project.id,
                project.name,
                project.description,
                project.status.value,
                json.dumps(project.tags, ensure_ascii=False),
                project.next_action,
                json.dumps(project.decisions, ensure_ascii=False),
                json.dumps(project.files, ensure_ascii=False),
                project.notes,
                project.created_at,
                now,
            ),
        )
        self._conn.commit()

    def get(self, project_id: str) -> Optional[ProjectCard]:
        row = self._conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return self._row_to_project(row) if row else None

    def list_active(self) -> list[ProjectCard]:
        rows = self._conn.execute(
            "SELECT * FROM projects WHERE status = 'active' ORDER BY updated_at DESC"
        ).fetchall()
        return [self._row_to_project(r) for r in rows]

    def list_all(self, limit: int = 50) -> list[ProjectCard]:
        rows = self._conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_project(r) for r in rows]

    def search_by_name(self, query: str) -> list[ProjectCard]:
        rows = self._conn.execute(
            "SELECT * FROM projects WHERE name LIKE ? ORDER BY updated_at DESC",
            (f"%{query}%",),
        ).fetchall()
        return [self._row_to_project(r) for r in rows]

    @staticmethod
    def _row_to_project(row: sqlite3.Row) -> ProjectCard:
        d = dict(row)
        d["tags"]      = json.loads(d.get("tags", "[]"))
        d["decisions"] = json.loads(d.get("decisions", "[]"))
        d["files"]     = json.loads(d.get("files", "[]"))
        d["status"]    = ProjectStatus(d.get("status", "active"))
        return ProjectCard(**d)
