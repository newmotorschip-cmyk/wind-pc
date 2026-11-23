"""
Fila de missões persistida em SQLite.
Suporta criação, listagem, atualização e retomada entre sessões.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

from .mission import Mission, MissionStatus, MissionStep, MissionType

DB_PATH = Path(os.getenv("WIND_DB_PATH", "data/wind.db"))


def _get_conn(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS missions (
            id           TEXT PRIMARY KEY,
            title        TEXT NOT NULL,
            mission_type TEXT DEFAULT 'generic',
            status       TEXT DEFAULT 'pending',
            project_id   TEXT,
            plan         TEXT DEFAULT '[]',
            current_step INTEGER DEFAULT 0,
            context      TEXT DEFAULT '{}',
            session_id   TEXT DEFAULT '',
            created_at   REAL,
            updated_at   REAL
        );
        CREATE INDEX IF NOT EXISTS idx_missions_status     ON missions(status);
        CREATE INDEX IF NOT EXISTS idx_missions_project_id ON missions(project_id);
    """)
    conn.commit()


class MissionQueue:
    def __init__(self, path: Path = DB_PATH) -> None:
        self._conn = _get_conn(path)
        _migrate(self._conn)

    def save(self, mission: Mission) -> None:
        now = time.time()
        mission.updated_at = now
        self._conn.execute(
            """INSERT OR REPLACE INTO missions
               (id, title, mission_type, status, project_id, plan, current_step, context, session_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mission.id,
                mission.title,
                mission.mission_type.value,
                mission.status.value,
                mission.project_id,
                json.dumps([s.to_dict() for s in mission.plan], ensure_ascii=False),
                mission.current_step,
                json.dumps(mission.context, ensure_ascii=False),
                mission.session_id,
                mission.created_at,
                now,
            ),
        )
        self._conn.commit()

    def get(self, mission_id: str) -> Optional[Mission]:
        row = self._conn.execute(
            "SELECT * FROM missions WHERE id = ?", (mission_id,)
        ).fetchone()
        return self._row_to_mission(row) if row else None

    def list_active(self) -> list[Mission]:
        rows = self._conn.execute(
            "SELECT * FROM missions WHERE status IN ('pending','running','paused') ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_mission(r) for r in rows]

    def list_all(self, limit: int = 20) -> list[Mission]:
        rows = self._conn.execute(
            "SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_mission(r) for r in rows]

    def list_for_project(self, project_id: str) -> list[Mission]:
        rows = self._conn.execute(
            "SELECT * FROM missions WHERE project_id = ? ORDER BY created_at DESC", (project_id,)
        ).fetchall()
        return [self._row_to_mission(r) for r in rows]

    @staticmethod
    def _row_to_mission(row: sqlite3.Row) -> Mission:
        d = dict(row)
        plan = [MissionStep.from_dict(s) for s in json.loads(d.pop("plan", "[]"))]
        context = json.loads(d.pop("context", "{}"))
        d["mission_type"] = MissionType(d.get("mission_type", "generic"))
        d["status"] = MissionStatus(d.get("status", "pending"))
        return Mission(**{**d, "plan": plan, "context": context})
