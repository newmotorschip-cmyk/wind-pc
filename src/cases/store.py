"""
Persistência de ServiceCases em SQLite com FTS5 para busca por similaridade.
Dados PII (placa, VIN) ficam locais — nunca exportar sem anonimizar.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

from .case import CaseResult, CaseStatus, EcuInfo, ServiceCase, VehicleInfo

DB_PATH = Path(os.getenv("WIND_DB_PATH", "data/wind.db"))


def _get_conn(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS service_cases (
            id           TEXT PRIMARY KEY,
            queixa       TEXT NOT NULL,
            vehicle      TEXT DEFAULT '{}',
            ecu          TEXT DEFAULT '{}',
            dtcs         TEXT DEFAULT '[]',
            hypotheses   TEXT DEFAULT '[]',
            actions      TEXT DEFAULT '[]',
            result       TEXT DEFAULT 'unknown',
            lessons      TEXT DEFAULT '[]',
            time_minutes INTEGER DEFAULT 0,
            cost_brl     REAL DEFAULT 0.0,
            status       TEXT DEFAULT 'open',
            file_hashes  TEXT DEFAULT '[]',
            session_id   TEXT DEFAULT '',
            created_at   REAL,
            updated_at   REAL,
            closed_at    REAL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS cases_fts
            USING fts5(
                id UNINDEXED,
                similarity_text,
                content=service_cases,
                content_rowid=rowid,
                tokenize='unicode61'
            );

        CREATE TRIGGER IF NOT EXISTS cases_fts_insert
            AFTER INSERT ON service_cases BEGIN
                INSERT INTO cases_fts(rowid, id, similarity_text)
                VALUES (new.rowid, new.id, new.queixa || ' ' ||
                    json_extract(new.vehicle,'$.marca') || ' ' ||
                    json_extract(new.vehicle,'$.modelo') || ' ' ||
                    json_extract(new.vehicle,'$.motor') || ' ' ||
                    json_extract(new.ecu,'$.fabricante') || ' ' ||
                    json_extract(new.ecu,'$.referencia'));
            END;

        CREATE TRIGGER IF NOT EXISTS cases_fts_update
            AFTER UPDATE ON service_cases BEGIN
                DELETE FROM cases_fts WHERE rowid = old.rowid;
                INSERT INTO cases_fts(rowid, id, similarity_text)
                VALUES (new.rowid, new.id, new.queixa || ' ' ||
                    json_extract(new.vehicle,'$.marca') || ' ' ||
                    json_extract(new.vehicle,'$.modelo') || ' ' ||
                    json_extract(new.vehicle,'$.motor') || ' ' ||
                    json_extract(new.ecu,'$.fabricante') || ' ' ||
                    json_extract(new.ecu,'$.referencia'));
            END;

        CREATE TRIGGER IF NOT EXISTS cases_fts_delete
            AFTER DELETE ON service_cases BEGIN
                DELETE FROM cases_fts WHERE rowid = old.rowid;
            END;

        CREATE INDEX IF NOT EXISTS idx_cases_status     ON service_cases(status);
        CREATE INDEX IF NOT EXISTS idx_cases_ecu_ref    ON service_cases(json_extract(ecu, '$.referencia'));
        CREATE INDEX IF NOT EXISTS idx_cases_vehicle    ON service_cases(json_extract(vehicle, '$.modelo'));
    """)
    conn.commit()


class CaseStore:
    def __init__(self, path: Path = DB_PATH) -> None:
        self._conn = _get_conn(path)
        _migrate(self._conn)

    @staticmethod
    def _sanitize_fts(query: str) -> str:
        import re
        words = re.findall(r'[\wÀ-ɏ]+', query)
        words = [w for w in words if w.upper() not in ("AND", "OR", "NOT")]
        return ' '.join(words) if words else "servico"

    def save(self, case: ServiceCase) -> None:
        now = time.time()
        case.updated_at = now
        self._conn.execute(
            """INSERT OR REPLACE INTO service_cases
               (id, queixa, vehicle, ecu, dtcs, hypotheses, actions, result, lessons,
                time_minutes, cost_brl, status, file_hashes, session_id, created_at, updated_at, closed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case.id,
                case.queixa,
                json.dumps(case.vehicle.to_dict(), ensure_ascii=False),
                json.dumps(case.ecu.to_dict(), ensure_ascii=False),
                json.dumps(case.dtcs, ensure_ascii=False),
                json.dumps(case.hypotheses, ensure_ascii=False),
                json.dumps(case.actions, ensure_ascii=False),
                case.result.value,
                json.dumps(case.lessons, ensure_ascii=False),
                case.time_minutes,
                case.cost_brl,
                case.status.value,
                json.dumps(case.file_hashes, ensure_ascii=False),
                case.session_id,
                case.created_at,
                now,
                case.closed_at,
            ),
        )
        self._conn.commit()

    def get(self, case_id: str) -> Optional[ServiceCase]:
        row = self._conn.execute(
            "SELECT * FROM service_cases WHERE id = ?", (case_id,)
        ).fetchone()
        return self._row_to_case(row) if row else None

    def search_similar(self, query: str, limit: int = 5) -> list[ServiceCase]:
        """Busca casos similares por veículo, ECU e sintoma via FTS5."""
        safe_q = self._sanitize_fts(query)
        try:
            rows = self._conn.execute(
                """SELECT sc.* FROM service_cases sc
                   INNER JOIN cases_fts ON sc.rowid = cases_fts.rowid
                   WHERE cases_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (safe_q, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        return [self._row_to_case(r) for r in rows]

    def list_open(self) -> list[ServiceCase]:
        rows = self._conn.execute(
            "SELECT * FROM service_cases WHERE status = 'open' ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_case(r) for r in rows]

    def list_all(self, limit: int = 50) -> list[ServiceCase]:
        rows = self._conn.execute(
            "SELECT * FROM service_cases ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_case(r) for r in rows]

    def list_by_ecu(self, referencia: str) -> list[ServiceCase]:
        rows = self._conn.execute(
            "SELECT * FROM service_cases WHERE json_extract(ecu,'$.referencia') = ? ORDER BY created_at DESC",
            (referencia,),
        ).fetchall()
        return [self._row_to_case(r) for r in rows]

    @staticmethod
    def _row_to_case(row: sqlite3.Row) -> ServiceCase:
        d = dict(row)
        vehicle = VehicleInfo.from_dict(json.loads(d.pop("vehicle", "{}")))
        ecu     = EcuInfo.from_dict(json.loads(d.pop("ecu", "{}")))
        for f in ("dtcs", "hypotheses", "actions", "lessons", "file_hashes"):
            d[f] = json.loads(d.get(f, "[]"))
        d["result"] = CaseResult(d.get("result", "unknown"))
        d["status"] = CaseStatus(d.get("status", "open"))
        return ServiceCase(**{**d, "vehicle": vehicle, "ecu": ecu})
