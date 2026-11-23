"""
Armazenamento SQLite para dados financeiros — Fase 7.
Dados de classe FINANCEIRO ficam locais, nunca ao modelo remoto.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date
from pathlib import Path
from typing import Optional

from .account import Account, AccountType, Transaction, TransactionCategory


_DDL = """
CREATE TABLE IF NOT EXISTS fin_accounts (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    bank_name    TEXT NOT NULL,
    account_type TEXT NOT NULL,
    agency       TEXT DEFAULT '',
    account_number TEXT DEFAULT '',
    balance_brl  REAL DEFAULT 0.0,
    updated_at   REAL NOT NULL,
    currency     TEXT DEFAULT 'BRL',
    active       INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fin_transactions (
    id           TEXT PRIMARY KEY,
    account_id   TEXT NOT NULL,
    date         TEXT NOT NULL,
    description  TEXT NOT NULL,
    value_brl    REAL NOT NULL,
    category     TEXT NOT NULL,
    raw_memo     TEXT DEFAULT '',
    source_file  TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_fin_txn_account ON fin_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_fin_txn_date    ON fin_transactions(date);
"""


class FinanceStore:
    def __init__(self, path: Path | str = "data/wind.db") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)

    # ── Accounts ──────────────────────────────────────────────────────────────

    def save_account(self, account: Account) -> Account:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO fin_accounts
                    (id, name, bank_name, account_type, agency, account_number,
                     balance_brl, updated_at, currency, active)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, bank_name=excluded.bank_name,
                    account_type=excluded.account_type, agency=excluded.agency,
                    balance_brl=excluded.balance_brl, updated_at=excluded.updated_at,
                    currency=excluded.currency, active=excluded.active
            """, (
                account.id, account.name, account.bank_name, account.account_type.value,
                account.agency, account.account_number, account.balance_brl,
                account.updated_at, account.currency, int(account.active),
            ))
        return account

    def get_account(self, account_id: str) -> Optional[Account]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM fin_accounts WHERE id=?", (account_id,)).fetchone()
        return Account.from_dict(dict(row)) if row else None

    def list_accounts(self, active_only: bool = True) -> list[Account]:
        q = "SELECT * FROM fin_accounts"
        args: tuple = ()
        if active_only:
            q += " WHERE active=1"
        q += " ORDER BY bank_name, name"
        with self._connect() as conn:
            rows = conn.execute(q, args).fetchall()
        return [Account.from_dict(dict(r)) for r in rows]

    def find_or_create_account(self, name: str, bank_name: str,
                                account_type: AccountType = AccountType.CORRENTE) -> Account:
        accounts = self.list_accounts(active_only=False)
        for a in accounts:
            if a.bank_name == bank_name and a.name == name:
                return a
        import time
        account = Account(
            id=str(uuid.uuid4())[:16], name=name, bank_name=bank_name,
            account_type=account_type, updated_at=time.time(),
        )
        return self.save_account(account)

    # ── Transactions ──────────────────────────────────────────────────────────

    def save_transactions(self, transactions: list[Transaction]) -> int:
        """Insere ou ignora duplicatas (por id). Retorna o número de inserções."""
        inserted = 0
        with self._connect() as conn:
            for txn in transactions:
                try:
                    cursor = conn.execute("""
                        INSERT OR IGNORE INTO fin_transactions
                            (id, account_id, date, description, value_brl,
                             category, raw_memo, source_file)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (
                        txn.id, txn.account_id, txn.date.isoformat(),
                        txn.description, txn.value_brl, txn.category.value,
                        txn.raw_memo, txn.source_file,
                    ))
                    if cursor.rowcount:
                        inserted += 1
                except sqlite3.Error:
                    pass
        return inserted

    def list_transactions(
        self,
        account_id: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        limit: int = 500,
    ) -> list[Transaction]:
        q = "SELECT * FROM fin_transactions WHERE 1=1"
        args: list = []
        if account_id:
            q += " AND account_id=?"
            args.append(account_id)
        if start:
            q += " AND date>=?"
            args.append(start.isoformat())
        if end:
            q += " AND date<=?"
            args.append(end.isoformat())
        q += f" ORDER BY date DESC LIMIT {limit}"
        with self._connect() as conn:
            rows = conn.execute(q, args).fetchall()
        return [Transaction.from_dict(dict(r)) for r in rows]

    def get_balance(self, account_id: str) -> float:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT SUM(value_brl) FROM fin_transactions WHERE account_id=?",
                (account_id,)
            ).fetchone()
        return float(row[0] or 0.0)

    def totals_by_category(
        self,
        account_id: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> dict[str, float]:
        q = "SELECT category, SUM(value_brl) FROM fin_transactions WHERE 1=1"
        args: list = []
        if account_id:
            q += " AND account_id=?"
            args.append(account_id)
        if start:
            q += " AND date>=?"
            args.append(start.isoformat())
        if end:
            q += " AND date<=?"
            args.append(end.isoformat())
        q += " GROUP BY category"
        with self._connect() as conn:
            rows = conn.execute(q, args).fetchall()
        return {r[0]: float(r[1]) for r in rows}

    def monthly_totals(self, account_id: Optional[str] = None, year: Optional[int] = None) -> list[dict]:
        q = "SELECT substr(date,1,7) as month, SUM(value_brl) FROM fin_transactions WHERE 1=1"
        args: list = []
        if account_id:
            q += " AND account_id=?"
            args.append(account_id)
        if year:
            q += " AND date LIKE ?"
            args.append(f"{year}-%")
        q += " GROUP BY month ORDER BY month"
        with self._connect() as conn:
            rows = conn.execute(q, args).fetchall()
        return [{"month": r[0], "total": float(r[1])} for r in rows]
