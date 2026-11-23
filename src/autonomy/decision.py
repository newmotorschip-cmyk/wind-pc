"""
Registro e armazenamento de decisões da WIND — Fase 8.

Toda decisão relevante gera um DecisionRecord com:
  pedido, opções, evidências, risco, reversibilidade,
  confiança, escolha, quem aprovou e resultado.
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


class DecisionStatus(str, Enum):
    PENDING   = "pending"    # aguardando aprovação
    APPROVED  = "approved"   # aprovada (por Felipe ou autônoma)
    REJECTED  = "rejected"   # rejeitada
    EXECUTED  = "executed"   # executada
    REVERTED  = "reverted"   # revertida


class RiskLevel(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

    def numeric(self) -> int:
        return {"low": 1, "medium": 2, "high": 3, "critical": 4}[self.value]


@dataclass
class DecisionRecord:
    id: str
    request: str
    options: list[str]
    evidence: str
    risk: RiskLevel
    reversible: bool
    confidence: float          # 0.0 – 1.0
    chosen_option: str
    approved_by: str           # "" = autonomia; "Felipe" = aprovação explícita
    status: DecisionStatus
    result: str = ""
    created_at: float = field(default_factory=time.time)
    executed_at: float = 0.0
    session_id: str = ""
    domain: str = ""

    def summary(self) -> str:
        icon = "🤖" if not self.approved_by else "✅"
        rev  = "reversível" if self.reversible else "irreversível"
        return (
            f"{icon} [{self.id[:8]}] {self.request[:60]}\n"
            f"   Risco: {self.risk.value} | {rev} | Confiança: {self.confidence:.0%} | "
            f"Status: {self.status.value}"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request": self.request,
            "options": self.options,
            "evidence": self.evidence,
            "risk": self.risk.value,
            "reversible": self.reversible,
            "confidence": self.confidence,
            "chosen_option": self.chosen_option,
            "approved_by": self.approved_by,
            "status": self.status.value,
            "result": self.result,
            "created_at": self.created_at,
            "executed_at": self.executed_at,
            "session_id": self.session_id,
            "domain": self.domain,
        }

    @staticmethod
    def from_dict(d: dict) -> "DecisionRecord":
        return DecisionRecord(
            id=d["id"], request=d["request"],
            options=json.loads(d["options"]) if isinstance(d["options"], str) else d["options"],
            evidence=d["evidence"], risk=RiskLevel(d["risk"]),
            reversible=bool(d["reversible"]), confidence=float(d["confidence"]),
            chosen_option=d["chosen_option"], approved_by=d.get("approved_by", ""),
            status=DecisionStatus(d["status"]), result=d.get("result", ""),
            created_at=float(d.get("created_at", 0)),
            executed_at=float(d.get("executed_at", 0)),
            session_id=d.get("session_id", ""), domain=d.get("domain", ""),
        )


_DDL = """
CREATE TABLE IF NOT EXISTS decisions (
    id           TEXT PRIMARY KEY,
    request      TEXT NOT NULL,
    options      TEXT NOT NULL,
    evidence     TEXT NOT NULL,
    risk         TEXT NOT NULL,
    reversible   INTEGER NOT NULL,
    confidence   REAL NOT NULL,
    chosen_option TEXT NOT NULL,
    approved_by  TEXT DEFAULT '',
    status       TEXT NOT NULL,
    result       TEXT DEFAULT '',
    created_at   REAL NOT NULL,
    executed_at  REAL DEFAULT 0,
    session_id   TEXT DEFAULT '',
    domain       TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_dec_status    ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_dec_created   ON decisions(created_at);
"""


class DecisionStore:
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

    def save(self, record: DecisionRecord) -> DecisionRecord:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO decisions
                    (id, request, options, evidence, risk, reversible, confidence,
                     chosen_option, approved_by, status, result, created_at,
                     executed_at, session_id, domain)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status, result=excluded.result,
                    executed_at=excluded.executed_at, approved_by=excluded.approved_by
            """, (
                record.id, record.request, json.dumps(record.options),
                record.evidence, record.risk.value, int(record.reversible),
                record.confidence, record.chosen_option, record.approved_by,
                record.status.value, record.result, record.created_at,
                record.executed_at, record.session_id, record.domain,
            ))
        return record

    def get(self, record_id: str) -> Optional[DecisionRecord]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM decisions WHERE id=?", (record_id,)).fetchone()
        return DecisionRecord.from_dict(dict(row)) if row else None

    def list_pending(self) -> list[DecisionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM decisions WHERE status=? ORDER BY created_at DESC",
                (DecisionStatus.PENDING.value,)
            ).fetchall()
        return [DecisionRecord.from_dict(dict(r)) for r in rows]

    def list_recent(self, limit: int = 20) -> list[DecisionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [DecisionRecord.from_dict(dict(r)) for r in rows]

    def stats(self, since: float = 0.0) -> dict:
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM decisions WHERE created_at>=?", (since,)
            ).fetchone()[0]
            autonomous = conn.execute(
                "SELECT COUNT(*) FROM decisions WHERE approved_by='' AND created_at>=?", (since,)
            ).fetchone()[0]
            by_status = conn.execute(
                "SELECT status, COUNT(*) FROM decisions WHERE created_at>=? GROUP BY status",
                (since,)
            ).fetchall()
        return {
            "total": total,
            "autonomous": autonomous,
            "approved_by_felipe": total - autonomous,
            "by_status": {r[0]: r[1] for r in by_status},
        }
