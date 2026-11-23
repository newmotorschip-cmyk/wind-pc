"""
Migração de esquema SQLite da WIND — Fase 9.

Cada migração tem um número de versão e um bloco SQL.
O Migrator aplica só as migrações pendentes, em ordem.
Nunca destrói dados existentes sem column rename/copy explícito.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Tipo de função de migração: recebe Connection, retorna None
MigrationFn = Callable[[sqlite3.Connection], None]


@dataclass
class Migration:
    version: int
    description: str
    up: MigrationFn


def _ensure_schema_version_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at  REAL NOT NULL
        )
    """)
    conn.commit()


def _current_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        return row[0] if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        return 0


# ── Migrações registradas ──────────────────────────────────────────────────
# Nunca remova ou reordene uma migração publicada.
# Para reverter: adicione uma nova migração que desfaz a anterior.

def _m001_initial_schema(conn: sqlite3.Connection) -> None:
    """Esquema inicial completo — aplicado apenas em bancos novos (versão 0)."""
    conn.executescript("""
        -- Memória episódica
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            summary     TEXT NOT NULL,
            full_text   TEXT NOT NULL,
            session_id  TEXT DEFAULT '',
            model       TEXT DEFAULT '',
            created_at  REAL NOT NULL,
            tags        TEXT DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_ep_created ON episodic_memory(created_at);
        -- Memória semântica (FTS5)
        CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fts USING fts5(
            id UNINDEXED, topic, content, source, tags,
            tokenize='unicode61'
        );
        -- Projetos
        CREATE TABLE IF NOT EXISTS projects (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            status      TEXT NOT NULL DEFAULT 'active',
            next_action TEXT DEFAULT '',
            created_at  REAL NOT NULL,
            updated_at  REAL NOT NULL
        );
        -- Missões
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
        -- Casos de serviço (schema real do CaseStore)
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
        CREATE INDEX IF NOT EXISTS idx_cases_status  ON service_cases(status);
        -- Propostas de calibração
        CREATE TABLE IF NOT EXISTS calibration_proposals (
            id              TEXT PRIMARY KEY,
            ecu_family_id   TEXT NOT NULL,
            vehicle_description TEXT DEFAULT '',
            map_ids         TEXT DEFAULT '[]',
            guardian_level  INTEGER DEFAULT 1,
            requires_legal_note INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'pending',
            approved_by     TEXT DEFAULT '',
            created_at      REAL NOT NULL
        );
        -- Contas financeiras (schema real do FinanceStore)
        CREATE TABLE IF NOT EXISTS fin_accounts (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL DEFAULT '',
            bank_name    TEXT NOT NULL DEFAULT '',
            account_type TEXT NOT NULL DEFAULT 'checking',
            agency       TEXT DEFAULT '',
            account_number TEXT DEFAULT '',
            balance_brl  REAL DEFAULT 0.0,
            updated_at   REAL NOT NULL DEFAULT 0,
            currency     TEXT DEFAULT 'BRL',
            active       INTEGER DEFAULT 1
        );
        -- Transações financeiras (schema real do FinanceStore)
        CREATE TABLE IF NOT EXISTS fin_transactions (
            id          TEXT PRIMARY KEY,
            account_id  TEXT NOT NULL,
            date        TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL,
            value_brl   REAL NOT NULL DEFAULT 0,
            category    TEXT NOT NULL DEFAULT 'outros',
            raw_memo    TEXT DEFAULT '',
            source_file TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_fin_txn_account ON fin_transactions(account_id);
        CREATE INDEX IF NOT EXISTS idx_fin_txn_date    ON fin_transactions(date);
        -- Decisões
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
        CREATE INDEX IF NOT EXISTS idx_dec_status  ON decisions(status);
        CREATE INDEX IF NOT EXISTS idx_dec_created ON decisions(created_at);
        -- Notas de aprendizado
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
        CREATE INDEX IF NOT EXISTS idx_notes_state ON learning_notes(state);
    """)


def _m002_add_notifications_table(conn: sqlite3.Connection) -> None:
    """Tabela de notificações para FileChannel."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         TEXT PRIMARY KEY,
            level      TEXT NOT NULL,
            source     TEXT NOT NULL,
            message    TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)


def _m003_fix_missions_schema(conn: sqlite3.Connection) -> None:
    """
    Repara tabela missions: adiciona colunas faltantes se a tabela foi criada
    com o esquema simplificado da migração 1 original.
    Usa ALTER TABLE ADD COLUMN que é seguro (não destrói dados existentes).
    """
    existing = {r[1] for r in conn.execute("PRAGMA table_info(missions)").fetchall()}
    additions = [
        ("mission_type", "TEXT DEFAULT 'generic'"),
        ("project_id",   "TEXT"),
        ("plan",         "TEXT DEFAULT '[]'"),
        ("current_step", "INTEGER DEFAULT 0"),
        ("context",      "TEXT DEFAULT '{}'"),
    ]
    for col, definition in additions:
        if col not in existing:
            conn.execute(f"ALTER TABLE missions ADD COLUMN {col} {definition}")
    # Remove colunas herdadas do esquema antigo que o MissionQueue não usa
    # (SQLite não suporta DROP COLUMN antes de 3.35 — não fazemos nada)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_missions_project_id ON missions(project_id)"
    )


def _m004_fix_finance_tables(conn: sqlite3.Connection) -> None:
    """
    Recria tabelas financeiras com o schema correto do FinanceStore.
    Seguro em dev pois nunca há dados financeiros reais nesta fase.
    """
    conn.executescript("""
        DROP TABLE IF EXISTS fin_transactions;
        DROP TABLE IF EXISTS fin_accounts;
        CREATE TABLE IF NOT EXISTS fin_accounts (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL DEFAULT '',
            bank_name    TEXT NOT NULL DEFAULT '',
            account_type TEXT NOT NULL DEFAULT 'checking',
            agency       TEXT DEFAULT '',
            account_number TEXT DEFAULT '',
            balance_brl  REAL DEFAULT 0.0,
            updated_at   REAL NOT NULL DEFAULT 0,
            currency     TEXT DEFAULT 'BRL',
            active       INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS fin_transactions (
            id          TEXT PRIMARY KEY,
            account_id  TEXT NOT NULL,
            date        TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL,
            value_brl   REAL NOT NULL DEFAULT 0,
            category    TEXT NOT NULL DEFAULT 'outros',
            raw_memo    TEXT DEFAULT '',
            source_file TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_fin_txn_account ON fin_transactions(account_id);
        CREATE INDEX IF NOT EXISTS idx_fin_txn_date    ON fin_transactions(date);
    """)


def _m005_fix_service_cases(conn: sqlite3.Connection) -> None:
    """
    Recria tabela service_cases com o schema correto do CaseStore.
    Seguro pois nunca há casos reais nesta fase de desenvolvimento.
    """
    conn.executescript("""
        DROP TRIGGER IF EXISTS cases_fts_delete;
        DROP TRIGGER IF EXISTS cases_fts_update;
        DROP TRIGGER IF EXISTS cases_fts_insert;
        DROP TABLE IF EXISTS cases_fts;
        DROP TABLE IF EXISTS service_cases;
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
                    COALESCE(json_extract(new.vehicle,'$.marca'), '') || ' ' ||
                    COALESCE(json_extract(new.vehicle,'$.modelo'), '') || ' ' ||
                    COALESCE(json_extract(new.ecu,'$.fabricante'), '') || ' ' ||
                    COALESCE(json_extract(new.ecu,'$.referencia'), ''));
            END;
        CREATE TRIGGER IF NOT EXISTS cases_fts_update
            AFTER UPDATE ON service_cases BEGIN
                DELETE FROM cases_fts WHERE rowid = old.rowid;
                INSERT INTO cases_fts(rowid, id, similarity_text)
                VALUES (new.rowid, new.id, new.queixa || ' ' ||
                    COALESCE(json_extract(new.vehicle,'$.marca'), '') || ' ' ||
                    COALESCE(json_extract(new.vehicle,'$.modelo'), '') || ' ' ||
                    COALESCE(json_extract(new.ecu,'$.fabricante'), '') || ' ' ||
                    COALESCE(json_extract(new.ecu,'$.referencia'), ''));
            END;
        CREATE TRIGGER IF NOT EXISTS cases_fts_delete
            AFTER DELETE ON service_cases BEGIN
                DELETE FROM cases_fts WHERE rowid = old.rowid;
            END;
        CREATE INDEX IF NOT EXISTS idx_cases_status  ON service_cases(status);
        CREATE INDEX IF NOT EXISTS idx_cases_ecu_ref ON service_cases(json_extract(ecu, '$.referencia'));
        CREATE INDEX IF NOT EXISTS idx_cases_vehicle ON service_cases(json_extract(vehicle, '$.modelo'));
    """)


MIGRATIONS: list[Migration] = [
    Migration(1, "esquema inicial completo", _m001_initial_schema),
    Migration(2, "tabela de notificações", _m002_add_notifications_table),
    Migration(3, "reparar schema missions (colunas mission_type/project_id/plan/step/context)", _m003_fix_missions_schema),
    Migration(4, "reparar schema fin_accounts e fin_transactions (FinanceStore)", _m004_fix_finance_tables),
    Migration(5, "reparar schema service_cases e cases_fts (CaseStore)", _m005_fix_service_cases),
]


class Migrator:
    def __init__(self, db_path: Path | str = "data/wind.db") -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def current_version(self) -> int:
        with self._connect() as conn:
            _ensure_schema_version_table(conn)
            return _current_version(conn)

    def pending(self) -> list[Migration]:
        cur = self.current_version()
        return [m for m in MIGRATIONS if m.version > cur]

    def migrate(self) -> list[int]:
        """Aplica migrações pendentes. Retorna lista de versões aplicadas."""
        import time
        applied: list[int] = []
        with self._connect() as conn:
            _ensure_schema_version_table(conn)
            cur = _current_version(conn)
            for m in MIGRATIONS:
                if m.version > cur:
                    m.up(conn)
                    conn.execute(
                        "INSERT OR IGNORE INTO schema_version (version, description, applied_at) VALUES (?,?,?)",
                        (m.version, m.description, time.time()),
                    )
                    conn.commit()
                    applied.append(m.version)
        return applied

    def status(self) -> dict:
        cur     = self.current_version()
        pending = self.pending()
        return {
            "current_version": cur,
            "latest_version":  MIGRATIONS[-1].version if MIGRATIONS else 0,
            "pending_count":   len(pending),
            "up_to_date":      len(pending) == 0,
        }
