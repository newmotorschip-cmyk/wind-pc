"""
Armazena propostas de calibração em SQLite.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Optional

from .proposal import CalibrationProposal, ProposalStatus


class CalibrationStore:
    def __init__(self, path: Path | str = "data/wind.db") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS calibration_proposals (
                    id TEXT PRIMARY KEY,
                    ecu_family_id TEXT NOT NULL,
                    vehicle_description TEXT NOT NULL,
                    maps_json TEXT NOT NULL,
                    justification TEXT,
                    validation_plan TEXT,
                    guardian_level INTEGER,
                    requires_legal_note INTEGER,
                    legal_note TEXT,
                    status TEXT NOT NULL,
                    created_at REAL,
                    session_id TEXT,
                    original_file_hash TEXT,
                    approved_by TEXT,
                    approved_at REAL,
                    rejection_reason TEXT,
                    applied_at REAL
                )
            """)

    def save(self, p: CalibrationProposal) -> None:
        d = p.to_dict()
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO calibration_proposals VALUES (
                    :id, :ecu_family_id, :vehicle_description, :maps_json,
                    :justification, :validation_plan, :guardian_level,
                    :requires_legal_note, :legal_note, :status, :created_at,
                    :session_id, :original_file_hash, :approved_by,
                    :approved_at, :rejection_reason, :applied_at
                )
            """, {
                "id": d["id"],
                "ecu_family_id": d["ecu_family_id"],
                "vehicle_description": d["vehicle_description"],
                "maps_json": json.dumps(d["maps"]),
                "justification": d["justification"],
                "validation_plan": d["validation_plan"],
                "guardian_level": d["guardian_level"],
                "requires_legal_note": int(d["requires_legal_note"]),
                "legal_note": d["legal_note"],
                "status": d["status"],
                "created_at": d["created_at"],
                "session_id": d["session_id"],
                "original_file_hash": d["original_file_hash"],
                "approved_by": d["approved_by"],
                "approved_at": d["approved_at"],
                "rejection_reason": d["rejection_reason"],
                "applied_at": d["applied_at"],
            })

    def get(self, proposal_id: str) -> Optional[CalibrationProposal]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM calibration_proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
        return self._row_to_proposal(row) if row else None

    def list_pending(self) -> list[CalibrationProposal]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM calibration_proposals WHERE status IN (?, ?) ORDER BY created_at DESC",
                (ProposalStatus.PENDING.value, ProposalStatus.DRAFT.value),
            ).fetchall()
        return [self._row_to_proposal(r) for r in rows]

    def list_all(self) -> list[CalibrationProposal]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM calibration_proposals ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_proposal(r) for r in rows]

    def list_by_ecu(self, family_id: str) -> list[CalibrationProposal]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM calibration_proposals WHERE ecu_family_id = ? ORDER BY created_at DESC",
                (family_id,),
            ).fetchall()
        return [self._row_to_proposal(r) for r in rows]

    def _row_to_proposal(self, row: sqlite3.Row) -> CalibrationProposal:
        d = dict(row)
        d["maps"] = json.loads(d.pop("maps_json"))
        d["requires_legal_note"] = bool(d["requires_legal_note"])
        return CalibrationProposal.from_dict(d)
