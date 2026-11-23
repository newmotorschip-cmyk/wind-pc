"""
WindScheduler — agendador de tarefas da WIND.

Formatos de schedule suportados:
  "daily@HH:MM"              — diário na hora especificada
  "weekly@DOW@HH:MM"         — semanal (DOW: mon/tue/wed/thu/fri/sat/sun)
  "interval@SECONDS"         — a cada N segundos
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional


_DOW = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

_CHECK_INTERVAL = 60  # segundos entre iterações do loop

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id        TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    handler   TEXT NOT NULL,
    schedule  TEXT NOT NULL,
    params    TEXT DEFAULT '{}',
    enabled   INTEGER DEFAULT 1,
    last_run  TEXT,
    next_run  TEXT
);
"""

_DEFAULT_TASKS: list[dict] = [
    {
        "id": "backup_daily",
        "name": "Backup diário",
        "handler": "backup",
        "schedule": "daily@03:00",
    },
    {
        "id": "morning_summary",
        "name": "Resumo matinal",
        "handler": "morning_summary",
        "schedule": "daily@08:00",
    },
    {
        "id": "proactive_check",
        "name": "Verificação proativa",
        "handler": "proactive",
        "schedule": "interval@3600",
    },
    {
        "id": "weekly_report",
        "name": "Relatório semanal",
        "handler": "weekly_report",
        "schedule": "weekly@sun@09:00",
    },
]


@dataclass
class ScheduledTask:
    id: str
    name: str
    handler: str
    schedule: str
    params: dict = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "handler": self.handler,
            "schedule": self.schedule,
            "params": json.dumps(self.params),
            "enabled": int(self.enabled),
            "last_run": self.last_run,
            "next_run": self.next_run,
        }

    @classmethod
    def from_row(cls, row: tuple) -> "ScheduledTask":
        id_, name, handler, schedule, params_json, enabled, last_run, next_run = row
        return cls(
            id=id_,
            name=name,
            handler=handler,
            schedule=schedule,
            params=json.loads(params_json) if params_json else {},
            enabled=bool(enabled),
            last_run=last_run,
            next_run=next_run,
        )


class WindScheduler:
    """Agendador de tarefas persistido em SQLite com execução em background."""

    def __init__(self, db_path: str = "data/wind.db") -> None:
        self._db = Path(db_path)
        self._db.parent.mkdir(parents=True, exist_ok=True)
        self._handlers: dict[str, Callable] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._init_db()
        self._seed_defaults()

    # ── setup ──────────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        with sqlite3.connect(self._db) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def _seed_defaults(self) -> None:
        now = datetime.now()
        with sqlite3.connect(self._db) as conn:
            for t in _DEFAULT_TASKS:
                existing = conn.execute(
                    "SELECT id FROM scheduled_tasks WHERE id=?", (t["id"],)
                ).fetchone()
                if not existing:
                    next_run = _compute_next_run(t["schedule"], now).isoformat()
                    conn.execute(
                        "INSERT INTO scheduled_tasks VALUES (?,?,?,?,?,?,?,?)",
                        (t["id"], t["name"], t["handler"], t["schedule"],
                         "{}", 1, None, next_run),
                    )
            conn.commit()

    # ── handlers ───────────────────────────────────────────────────────────────

    def register_handler(self, name: str, fn: Callable) -> None:
        self._handlers[name] = fn

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="wind-scheduler"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _run_loop(self) -> None:
        while self._running:
            try:
                self._run_due_tasks()
            except Exception:
                pass
            for _ in range(_CHECK_INTERVAL):
                if not self._running:
                    return
                import time
                time.sleep(1)

    # ── execution ──────────────────────────────────────────────────────────────

    def _run_due_tasks(self) -> None:
        now = datetime.now()
        for task in self.list_tasks(enabled_only=True):
            if not task.next_run:
                continue
            try:
                next_dt = datetime.fromisoformat(task.next_run)
            except ValueError:
                continue
            if next_dt <= now:
                self._execute(task)

    def _execute(self, task: ScheduledTask) -> None:
        handler = self._handlers.get(task.handler)
        now_iso = datetime.now().isoformat()
        # Atualiza next_run antes de executar — evita execução dupla se handler demorar
        next_run = _compute_next_run(task.schedule, datetime.now())
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                "UPDATE scheduled_tasks SET last_run=?, next_run=? WHERE id=?",
                (now_iso, next_run.isoformat(), task.id),
            )
            conn.commit()
        if handler:
            try:
                handler(**task.params)
            except Exception:
                pass

    def check_missed(self) -> int:
        """Executa tarefas cujo next_run já passou (WIND estava desligada). Retorna contagem."""
        count = 0
        now = datetime.now()
        for task in self.list_tasks(enabled_only=True):
            if not task.next_run:
                continue
            try:
                next_dt = datetime.fromisoformat(task.next_run)
            except ValueError:
                continue
            if next_dt <= now:
                self._execute(task)
                count += 1
        return count

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def list_tasks(self, enabled_only: bool = False) -> list[ScheduledTask]:
        query = (
            "SELECT id,name,handler,schedule,params,enabled,last_run,next_run "
            "FROM scheduled_tasks"
        )
        if enabled_only:
            query += " WHERE enabled=1"
        query += " ORDER BY name"
        with sqlite3.connect(self._db) as conn:
            rows = conn.execute(query).fetchall()
        return [ScheduledTask.from_row(r) for r in rows]

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        with sqlite3.connect(self._db) as conn:
            row = conn.execute(
                "SELECT id,name,handler,schedule,params,enabled,last_run,next_run "
                "FROM scheduled_tasks WHERE id=?",
                (task_id,),
            ).fetchone()
        return ScheduledTask.from_row(row) if row else None

    def add_task(self, task: ScheduledTask) -> ScheduledTask:
        if not task.id:
            task.id = str(uuid.uuid4())[:8]
        if not task.next_run:
            task.next_run = _compute_next_run(task.schedule, datetime.now()).isoformat()
        d = task.to_dict()
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scheduled_tasks VALUES (?,?,?,?,?,?,?,?)",
                (d["id"], d["name"], d["handler"], d["schedule"],
                 d["params"], d["enabled"], d["last_run"], d["next_run"]),
            )
            conn.commit()
        return task

    def enable(self, task_id: str) -> bool:
        return self._set_enabled(task_id, True)

    def disable(self, task_id: str) -> bool:
        return self._set_enabled(task_id, False)

    def _set_enabled(self, task_id: str, value: bool) -> bool:
        with sqlite3.connect(self._db) as conn:
            conn.execute(
                "UPDATE scheduled_tasks SET enabled=? WHERE id=?",
                (int(value), task_id),
            )
            affected = conn.total_changes
            conn.commit()
        return affected > 0

    def run_now(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        self._execute(task)
        return True

    def summary(self) -> str:
        tasks = self.list_tasks()
        if not tasks:
            return "Nenhuma tarefa agendada."
        lines = [f"Tarefas agendadas ({len(tasks)}):"]
        for t in tasks:
            status = "✅" if t.enabled else "⏸️ "
            last = t.last_run[:16] if t.last_run else "nunca"
            next_ = t.next_run[:16] if t.next_run else "?"
            lines.append(f"  {status} [{t.id}] {t.name}")
            lines.append(f"       schedule: {t.schedule}")
            lines.append(f"       última:   {last}")
            lines.append(f"       próxima:  {next_}")
        return "\n".join(lines)


# ── helpers ────────────────────────────────────────────────────────────────────

def _compute_next_run(schedule: str, from_time: datetime) -> datetime:
    """Calcula próxima execução a partir de from_time."""
    parts = schedule.split("@")
    kind = parts[0].lower()

    if kind == "interval" and len(parts) >= 2:
        try:
            seconds = int(parts[1])
            return from_time + timedelta(seconds=seconds)
        except ValueError:
            pass

    if kind == "daily" and len(parts) >= 2:
        try:
            hh, mm = map(int, parts[1].split(":"))
            candidate = from_time.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if candidate <= from_time:
                candidate += timedelta(days=1)
            return candidate
        except (ValueError, IndexError):
            pass

    if kind == "weekly" and len(parts) >= 3:
        try:
            target_dow = _DOW.get(parts[1].lower(), 0)
            hh, mm = map(int, parts[2].split(":"))
            candidate = from_time.replace(hour=hh, minute=mm, second=0, microsecond=0)
            days_ahead = (target_dow - from_time.weekday()) % 7
            if days_ahead == 0 and candidate <= from_time:
                days_ahead = 7
            return candidate + timedelta(days=days_ahead)
        except (ValueError, IndexError):
            pass

    # Fallback: 1 hora
    return from_time + timedelta(hours=1)
