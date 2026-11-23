"""
Parser de extratos bancários da WIND — Fase 7.
Suporta OFX (Open Financial Exchange) e CSV genérico.

Dados de classe FINANCEIRO: ficam locais, nunca ao modelo.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from .account import Account, AccountType, Transaction, TransactionCategory, categorize


@dataclass
class ParseResult:
    account: Optional[Account]
    transactions: list[Transaction]
    source_file: str
    errors: list[str] = field(default_factory=list)
    format_detected: str = "unknown"

    @property
    def ok(self) -> bool:
        return len(self.transactions) > 0


# ─── OFX Parser ───────────────────────────────────────────────────────────────

class OFXParser:
    """
    Parser para formato OFX (Open Financial Exchange) — padrão bancário brasileiro.
    Suporta OFX 1.x (SGML-like) e OFX 2.x (XML).
    """

    def parse(self, path: Path | str) -> ParseResult:
        path = Path(path)
        if not path.exists():
            return ParseResult(None, [], str(path), [f"Arquivo não encontrado: {path}"])
        content = path.read_text(encoding="utf-8", errors="replace")
        return self._parse_content(content, str(path))

    def parse_string(self, content: str, source: str = "<string>") -> ParseResult:
        return self._parse_content(content, source)

    def _parse_content(self, content: str, source: str) -> ParseResult:
        errors: list[str] = []
        content_stripped = content.strip()

        # Detectar OFX 2.x (XML) vs 1.x (SGML)
        if "<?OFX" in content_stripped or "<OFX>" in content_stripped:
            return self._parse_xml(content_stripped, source)
        if "<OFX>" in content_stripped.upper():
            return self._parse_xml(content_stripped, source)
        # OFX 1.x: headers de texto antes do <OFX>
        return self._parse_sgml(content_stripped, source)

    def _parse_sgml(self, content: str, source: str) -> ParseResult:
        errors: list[str] = []

        # Extrai headers
        bank_id  = self._tag(content, "BANKID")  or self._tag(content, "FID") or "BANCO"
        acct_id  = self._tag(content, "ACCTID")  or ""
        acct_type_s = self._tag(content, "ACCTTYPE") or "CHECKING"
        balance_s   = self._tag(content, "BALAMT")   or "0"
        bank_name   = self._tag(content, "ORG")      or bank_id

        try:
            balance = float(balance_s.replace(",", "."))
        except ValueError:
            balance = 0.0
            errors.append(f"Saldo inválido: {balance_s!r}")

        acct_type = {
            "CHECKING": AccountType.CORRENTE,
            "SAVINGS":  AccountType.POUPANCA,
            "INVEST":   AccountType.INVESTIMENTO,
            "CREDITLINE": AccountType.CARTAO,
        }.get(acct_type_s.upper(), AccountType.OUTRO)

        account_id = hashlib.sha256(f"{bank_id}|{acct_id}".encode()).hexdigest()[:16]
        account = Account(
            id=account_id,
            name=f"Conta {acct_id[-4:] if len(acct_id) >= 4 else acct_id}",
            bank_name=bank_name,
            account_type=acct_type,
            account_number=acct_id,
            balance_brl=balance,
        )

        # Extrai transações
        txn_blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL | re.IGNORECASE)
        transactions: list[Transaction] = []
        for block in txn_blocks:
            try:
                txn = self._parse_sgml_transaction(block, account_id, source)
                if txn:
                    transactions.append(txn)
            except Exception as e:
                errors.append(f"Transação inválida: {e}")

        return ParseResult(account, transactions, source, errors, "ofx_sgml")

    def _parse_sgml_transaction(self, block: str, account_id: str, source: str) -> Optional[Transaction]:
        date_s = self._tag(block, "DTPOSTED") or self._tag(block, "DTUSER") or ""
        amt_s  = self._tag(block, "TRNAMT") or "0"
        memo   = self._tag(block, "MEMO")  or self._tag(block, "NAME") or ""
        name   = self._tag(block, "NAME")  or ""
        fitid  = self._tag(block, "FITID") or ""

        dt = self._parse_date(date_s)
        if dt is None:
            return None
        try:
            value = float(amt_s.replace(",", "."))
        except ValueError:
            return None

        description = memo or name or "Transação"
        category = categorize(description)
        tid = fitid or Transaction.make_id(account_id, dt, description, value)
        return Transaction(
            id=tid, account_id=account_id, date=dt,
            description=description[:200], value_brl=value,
            category=category, raw_memo=memo, source_file=source,
        )

    def _parse_xml(self, content: str, source: str) -> ParseResult:
        # Fallback: tenta via regex para OFX 2.x simples
        # (evita dependência de lxml/xml.etree para OFX com entidades inválidas)
        return self._parse_sgml(content, source)

    @staticmethod
    def _tag(text: str, tag: str) -> Optional[str]:
        m = re.search(rf"<{tag}>\s*([^<\n\r]+)", text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    @staticmethod
    def _parse_date(s: str) -> Optional[date]:
        s = s.strip()[:8]  # YYYYMMDD
        if len(s) < 8:
            return None
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except ValueError:
            return None


# ─── CSV Parser ───────────────────────────────────────────────────────────────

class CSVParser:
    """
    Parser de CSV genérico para extratos exportados pelo banco.
    Detecta automaticamente separador e mapeamento de colunas.
    Colunas esperadas (case-insensitive): data, descricao/historico, valor/debito/credito.
    """

    DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]
    DATE_COLUMNS = ["data", "date", "dt", "data lançamento", "data lanc"]
    DESC_COLUMNS = ["descricao", "descrição", "historico", "histórico", "memo", "nome", "description"]
    VAL_COLUMNS  = ["valor", "value", "amount", "montante"]
    DEB_COLUMNS  = ["debito", "débito", "saida", "saída"]
    CRE_COLUMNS  = ["credito", "crédito", "entrada"]

    def parse(self, path: Path | str, account: Optional[Account] = None) -> ParseResult:
        path = Path(path)
        if not path.exists():
            return ParseResult(None, [], str(path), [f"Arquivo não encontrado: {path}"])
        content = path.read_text(encoding="utf-8", errors="replace")
        return self._parse_content(content, str(path), account)

    def parse_string(self, content: str, source: str = "<string>", account: Optional[Account] = None) -> ParseResult:
        return self._parse_content(content, source, account)

    def _parse_content(self, content: str, source: str, account: Optional[Account]) -> ParseResult:
        errors: list[str] = []
        # Detectar separador
        sep = self._detect_separator(content)
        reader = csv.DictReader(io.StringIO(content), delimiter=sep)
        try:
            rows = list(reader)
        except csv.Error as e:
            return ParseResult(None, [], source, [f"CSV inválido: {e}"], "csv")

        if not rows:
            return ParseResult(account, [], source, ["CSV vazio ou sem cabeçalho"], "csv")

        headers = {h.lower().strip(): h for h in (reader.fieldnames or [])}

        # Detectar colunas
        date_col = self._find_col(headers, self.DATE_COLUMNS)
        desc_col = self._find_col(headers, self.DESC_COLUMNS)
        val_col  = self._find_col(headers, self.VAL_COLUMNS)
        deb_col  = self._find_col(headers, self.DEB_COLUMNS)
        cre_col  = self._find_col(headers, self.CRE_COLUMNS)

        if not date_col:
            errors.append("Coluna de data não encontrada")
            return ParseResult(account, [], source, errors, "csv")

        account_id = account.id if account else "csv_import"
        transactions: list[Transaction] = []
        for i, row in enumerate(rows):
            try:
                txn = self._parse_row(
                    row, i, account_id, source,
                    date_col, desc_col, val_col, deb_col, cre_col
                )
                if txn:
                    transactions.append(txn)
            except Exception as e:
                errors.append(f"Linha {i+2}: {e}")

        return ParseResult(account, transactions, source, errors, "csv")

    def _parse_row(
        self, row: dict, idx: int,
        account_id: str, source: str,
        date_col: str, desc_col: Optional[str],
        val_col: Optional[str], deb_col: Optional[str], cre_col: Optional[str],
    ) -> Optional[Transaction]:
        date_s = row.get(date_col, "").strip()
        dt = self._parse_date(date_s)
        if dt is None:
            return None

        desc = row.get(desc_col or "", "").strip() if desc_col else f"Transação {idx}"
        if not desc:
            desc = f"Transação {idx}"

        value: float = 0.0
        if val_col and row.get(val_col):
            value = self._parse_float(row[val_col])
        elif deb_col and cre_col:
            deb = self._parse_float(row.get(deb_col, "0"))
            cre = self._parse_float(row.get(cre_col, "0"))
            value = cre - abs(deb)

        if value == 0.0:
            return None

        category = categorize(desc)
        tid = Transaction.make_id(account_id, dt, desc, value)
        return Transaction(
            id=tid, account_id=account_id, date=dt,
            description=desc[:200], value_brl=value,
            category=category, raw_memo=desc, source_file=source,
        )

    def _parse_date(self, s: str) -> Optional[date]:
        from datetime import datetime
        s = s.strip()
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
        return None

    @staticmethod
    def _parse_float(s: str) -> float:
        s = s.strip().replace("R$", "").replace(" ", "")
        # Detectar formato brasileiro (1.234,56) vs padrão (1234.56 ou -250.00)
        if "," in s and "." in s:
            # Ambos: formato brasileiro 1.234,56 → 1234.56
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            # Só vírgula como decimal: 250,00 → 250.00
            s = s.replace(",", ".")
        # Else: ponto como decimal (formato padrão) — não alterar
        try:
            return float(s)
        except ValueError:
            return 0.0

    @staticmethod
    def _detect_separator(content: str) -> str:
        first_line = content.split("\n")[0]
        for sep in [";", ",", "\t", "|"]:
            if sep in first_line:
                return sep
        return ","

    @staticmethod
    def _find_col(headers: dict[str, str], candidates: list[str]) -> Optional[str]:
        for cand in candidates:
            if cand in headers:
                return headers[cand]
        return None


# ─── Facade ───────────────────────────────────────────────────────────────────

def parse_statement(path: Path | str, account: Optional[Account] = None) -> ParseResult:
    """Detecta o formato pelo conteúdo e chama o parser adequado."""
    path = Path(path)
    if not path.exists():
        return ParseResult(None, [], str(path), [f"Arquivo não encontrado: {path}"])
    content = path.read_text(encoding="utf-8", errors="replace")
    lower = content.lower()
    if "<ofx>" in lower or "<stmttrn>" in lower or "ofxheader" in lower:
        return OFXParser().parse(path)
    return CSVParser().parse(path, account=account)
