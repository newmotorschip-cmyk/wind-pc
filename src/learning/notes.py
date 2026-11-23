"""
Notas de aprendizado da WIND — Fase 8.

Toda nota nasce como PROPOSED (não validado).
Só vira VALIDATED depois que o Felipe valida ou um teste objetivo prova.
OBSOLETE marca notas superadas por conhecimento mais recente.

Regra invariante: a WIND nunca auto-valida suas próprias notas.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class NoteState(str, Enum):
    PROPOSED  = "proposed"    # não validado — padrão ao criar
    VALIDATED = "validated"   # validado por Felipe ou teste objetivo
    OBSOLETE  = "obsolete"    # superado por conhecimento mais recente


_DDL = """
CREATE TABLE IF NOT EXISTS learning_notes (
    id           TEXT PRIMARY KEY,
    topic        TEXT NOT NULL,
    content      TEXT NOT NULL,
    source       TEXT DEFAULT '',
    state        TEXT NOT NULL DEFAULT 'proposed',
    confidence   REAL DEFAULT 0.5,
    tags         TEXT DEFAULT '[]',
    created_at   REAL NOT NULL,
    validated_at REAL DEFAULT 0,
    validated_by TEXT DEFAULT '',
    session_id   TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_notes_topic ON learning_notes(topic);
CREATE INDEX IF NOT EXISTS idx_notes_state ON learning_notes(state);
"""


@dataclass
class LearningNote:
    id: str
    topic: str
    content: str
    source: str = ""
    state: NoteState = NoteState.PROPOSED
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    validated_at: float = 0.0
    validated_by: str = ""
    session_id: str = ""

    def summary_line(self) -> str:
        icon = {"proposed": "⏳", "validated": "✅", "obsolete": "🗑️"}.get(self.state.value, "·")
        tag_str = f" [{', '.join(self.tags[:3])}]" if self.tags else ""
        return f"{icon} [{self.id[:8]}] {self.topic[:55]}{tag_str} ({self.confidence:.0%})"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "topic": self.topic, "content": self.content,
            "source": self.source, "state": self.state.value,
            "confidence": self.confidence, "tags": self.tags,
            "created_at": self.created_at, "validated_at": self.validated_at,
            "validated_by": self.validated_by, "session_id": self.session_id,
        }

    @staticmethod
    def from_dict(d: dict) -> "LearningNote":
        tags = d.get("tags", "[]")
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = []
        return LearningNote(
            id=d["id"], topic=d["topic"], content=d["content"],
            source=d.get("source", ""), state=NoteState(d.get("state", "proposed")),
            confidence=float(d.get("confidence", 0.5)), tags=tags,
            created_at=float(d.get("created_at", 0)),
            validated_at=float(d.get("validated_at", 0)),
            validated_by=d.get("validated_by", ""),
            session_id=d.get("session_id", ""),
        )


class NoteStore:
    def __init__(self, path: Path | str = "data/wind.db") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_DDL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def save(self, note: LearningNote) -> LearningNote:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO learning_notes
                    (id, topic, content, source, state, confidence, tags,
                     created_at, validated_at, validated_by, session_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    state=excluded.state, confidence=excluded.confidence,
                    validated_at=excluded.validated_at, validated_by=excluded.validated_by,
                    content=excluded.content
            """, (
                note.id, note.topic, note.content, note.source,
                note.state.value, note.confidence,
                json.dumps(note.tags, ensure_ascii=False),
                note.created_at, note.validated_at, note.validated_by, note.session_id,
            ))
        return note

    def get(self, note_id: str) -> Optional[LearningNote]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM learning_notes WHERE id=?", (note_id,)).fetchone()
        return LearningNote.from_dict(dict(row)) if row else None

    def list_by_state(self, state: NoteState, limit: int = 50) -> list[LearningNote]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM learning_notes WHERE state=? ORDER BY created_at DESC LIMIT ?",
                (state.value, limit)
            ).fetchall()
        return [LearningNote.from_dict(dict(r)) for r in rows]

    def search(self, query: str, limit: int = 20) -> list[LearningNote]:
        q = f"%{query.lower()}%"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM learning_notes WHERE lower(topic) LIKE ? OR lower(content) LIKE ? "
                "ORDER BY created_at DESC LIMIT ?",
                (q, q, limit)
            ).fetchall()
        return [LearningNote.from_dict(dict(r)) for r in rows]

    def validate(self, note_id: str, validated_by: str = "Felipe") -> Optional[LearningNote]:
        """Valida uma nota. Nunca chamado pela WIND sobre si mesma."""
        note = self.get(note_id)
        if not note:
            return None
        note.state        = NoteState.VALIDATED
        note.validated_at = time.time()
        note.validated_by = validated_by
        return self.save(note)

    def mark_obsolete(self, note_id: str) -> Optional[LearningNote]:
        note = self.get(note_id)
        if not note:
            return None
        note.state = NoteState.OBSOLETE
        return self.save(note)

    def stats(self) -> dict:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT state, COUNT(*) FROM learning_notes GROUP BY state"
            ).fetchall()
        return {r[0]: r[1] for r in rows}


class NoteManager:
    def __init__(self, store: NoteStore) -> None:
        self._store = store

    def create(
        self, topic: str, content: str,
        source: str = "", confidence: float = 0.5,
        tags: Optional[list[str]] = None,
        session_id: str = "",
    ) -> LearningNote:
        note = LearningNote(
            id=str(uuid.uuid4()),
            topic=topic, content=content, source=source,
            state=NoteState.PROPOSED,
            confidence=min(max(confidence, 0.0), 1.0),
            tags=tags or [],
            session_id=session_id,
        )
        return self._store.save(note)

    def validate(self, note_id: str, validated_by: str = "Felipe") -> Optional[LearningNote]:
        return self._store.validate(note_id, validated_by)

    def mark_obsolete(self, note_id: str) -> Optional[LearningNote]:
        return self._store.mark_obsolete(note_id)

    def list_proposed(self, limit: int = 20) -> list[LearningNote]:
        return self._store.list_by_state(NoteState.PROPOSED, limit)

    def list_validated(self, limit: int = 20) -> list[LearningNote]:
        return self._store.list_by_state(NoteState.VALIDATED, limit)

    def search(self, query: str) -> list[LearningNote]:
        return self._store.search(query)

    def stats(self) -> dict:
        return self._store.stats()

    def context_for_topic(self, topic: str) -> str:
        """Retorna notas validadas relevantes para injetar no contexto do modelo."""
        notes = self._store.search(topic)
        validated = [n for n in notes if n.state == NoteState.VALIDATED]
        if not validated:
            return ""
        lines = [f"Conhecimento validado sobre '{topic}':"]
        for n in validated[:5]:
            lines.append(f"  [{n.confidence:.0%}] {n.topic}: {n.content[:120]}")
        return "\n".join(lines)
