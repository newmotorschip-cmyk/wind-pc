"""
Testes da Fase 7 — Finanças e contas (somente leitura).
"""
import sys
import uuid
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))


# ─── Categorização ────────────────────────────────────────────────────────────

class TestCategorize:
    def test_combustivel(self):
        from src.finance.account import categorize, TransactionCategory
        assert categorize("POSTO IPIRANGA - GASOLINA") == TransactionCategory.COMBUSTIVEL

    def test_pecas(self):
        from src.finance.account import categorize, TransactionCategory
        assert categorize("AUTOPECA CENTRO - FILTRO DE OLEO") == TransactionCategory.PECAS

    def test_impostos(self):
        from src.finance.account import categorize, TransactionCategory
        assert categorize("DAS - SIMPLES NACIONAL 06/2026") == TransactionCategory.IMPOSTOS

    def test_folha(self):
        from src.finance.account import categorize, TransactionCategory
        assert categorize("PAGAMENTO SALARIO FUNCIONARIO") == TransactionCategory.FOLHA_PAGAMENTO

    def test_aluguel(self):
        from src.finance.account import categorize, TransactionCategory
        assert categorize("Aluguel oficina junho") == TransactionCategory.ALUGUEL

    def test_receita_servico(self):
        from src.finance.account import categorize, TransactionCategory
        assert categorize("Pagamento ORD.SERV 1234 mao de obra") == TransactionCategory.RECEITA_SERVICO

    def test_outros_fallback(self):
        from src.finance.account import categorize, TransactionCategory
        assert categorize("Texto completamente desconhecido xyzabc") == TransactionCategory.OUTROS

    def test_corretora(self):
        from src.finance.account import categorize, TransactionCategory
        assert categorize("XP INVESTIMENTOS CDB LIQUIDEZ DIARIA") == TransactionCategory.CORRETORA


# ─── Account dataclass ────────────────────────────────────────────────────────

class TestAccount:
    def _make(self):
        from src.finance.account import Account, AccountType
        return Account(
            id="acc-test-1234",
            name="Conta Corrente",
            bank_name="Bradesco",
            account_type=AccountType.CORRENTE,
            account_number="123456789",
            balance_brl=5000.0,
        )

    def test_masked_number(self):
        acc = self._make()
        assert acc.masked_number() == "****6789"

    def test_summary_line_no_account_number(self):
        acc = self._make()
        line = acc.summary_line()
        assert "123456789" not in line  # número completo não aparece
        assert "6789" in line           # últimos 4 aparecem mascarados
        assert "Bradesco" in line

    def test_round_trip(self):
        from src.finance.account import Account
        acc = self._make()
        d = acc.to_dict()
        acc2 = Account.from_dict(d)
        assert acc2.id   == acc.id
        assert acc2.name == acc.name
        assert acc2.balance_brl == acc.balance_brl


# ─── Transaction dataclass ────────────────────────────────────────────────────

class TestTransaction:
    def test_make_id_deterministic(self):
        from src.finance.account import Transaction
        d = date(2026, 11, 1)
        id1 = Transaction.make_id("acc1", d, "COMBUSTIVEL", -150.0)
        id2 = Transaction.make_id("acc1", d, "COMBUSTIVEL", -150.0)
        assert id1 == id2

    def test_make_id_different_for_different_values(self):
        from src.finance.account import Transaction
        d = date(2026, 11, 1)
        id1 = Transaction.make_id("acc1", d, "COMBUSTIVEL", -150.0)
        id2 = Transaction.make_id("acc1", d, "COMBUSTIVEL", -200.0)
        assert id1 != id2

    def test_round_trip(self):
        from src.finance.account import Transaction, TransactionCategory
        t = Transaction(
            id="t1", account_id="acc1", date=date(2026, 11, 15),
            description="Teste", value_brl=-100.0,
            category=TransactionCategory.COMBUSTIVEL, raw_memo="raw", source_file="x.csv"
        )
        d  = t.to_dict()
        t2 = Transaction.from_dict(d)
        assert t2.id          == t.id
        assert t2.value_brl   == t.value_brl
        assert t2.category    == t.category
        assert t2.date        == t.date


# ─── OFX Parser ───────────────────────────────────────────────────────────────

_OFX_SAMPLE = """\
OFXHEADER:100
DATA:OFXSGML
VERSION:151
<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<BANKACCTFROM>
<BANKID>237</BANKID>
<ACCTID>12345-6</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>
<LEDGERBAL>
<BALAMT>8500.00</BALAMT>
<DTASOF>20261101120000</DTASOF>
</LEDGERBAL>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20261105</DTPOSTED>
<TRNAMT>-250.00</TRNAMT>
<FITID>T001</FITID>
<MEMO>POSTO IPIRANGA GASOLINA</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20261110</DTPOSTED>
<TRNAMT>3200.00</TRNAMT>
<FITID>T002</FITID>
<MEMO>SERVICO PRESTADO REVISAO VW GOLF</MEMO>
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

class TestOFXParser:
    def test_parse_string_ok(self):
        from src.finance.statement_parser import OFXParser
        result = OFXParser().parse_string(_OFX_SAMPLE)
        assert result.ok
        assert result.format_detected == "ofx_sgml"
        assert len(result.transactions) == 2

    def test_account_detected(self):
        from src.finance.statement_parser import OFXParser
        result = OFXParser().parse_string(_OFX_SAMPLE)
        assert result.account is not None
        assert result.account.balance_brl == 8500.0

    def test_transaction_values(self):
        from src.finance.statement_parser import OFXParser
        result = OFXParser().parse_string(_OFX_SAMPLE)
        values = {t.value_brl for t in result.transactions}
        assert -250.0 in values
        assert 3200.0 in values

    def test_categorization_in_parser(self):
        from src.finance.statement_parser import OFXParser
        from src.finance.account import TransactionCategory
        result = OFXParser().parse_string(_OFX_SAMPLE)
        cats = {t.category for t in result.transactions}
        assert TransactionCategory.COMBUSTIVEL in cats

    def test_missing_file_returns_error(self, tmp_path):
        from src.finance.statement_parser import OFXParser
        result = OFXParser().parse(tmp_path / "nao_existe.ofx")
        assert not result.ok
        assert len(result.errors) > 0


# ─── CSV Parser ───────────────────────────────────────────────────────────────

_CSV_SAMPLE = """\
Data;Descricao;Valor
05/11/2026;POSTO IPIRANGA GASOLINA;-250.00
10/11/2026;SERVICO PRESTADO REVISAO;3200.00
15/11/2026;ALUGUEL OFICINA;-1200.00
"""

class TestCSVParser:
    def test_parse_string_ok(self):
        from src.finance.statement_parser import CSVParser
        result = CSVParser().parse_string(_CSV_SAMPLE)
        assert result.ok
        assert result.format_detected == "csv"
        assert len(result.transactions) == 3

    def test_values_correct(self):
        from src.finance.statement_parser import CSVParser
        result = CSVParser().parse_string(_CSV_SAMPLE)
        values = [t.value_brl for t in result.transactions]
        assert -250.0 in values
        assert 3200.0 in values
        assert -1200.0 in values

    def test_categorization(self):
        from src.finance.statement_parser import CSVParser
        from src.finance.account import TransactionCategory
        result = CSVParser().parse_string(_CSV_SAMPLE)
        cats = {t.category for t in result.transactions}
        assert TransactionCategory.COMBUSTIVEL in cats
        assert TransactionCategory.ALUGUEL in cats

    def test_empty_csv_returns_no_transactions(self):
        from src.finance.statement_parser import CSVParser
        result = CSVParser().parse_string("Data;Descricao;Valor\n")
        assert len(result.transactions) == 0

    def test_detect_separator_semicolon(self):
        from src.finance.statement_parser import CSVParser
        sep = CSVParser._detect_separator("a;b;c")
        assert sep == ";"


# ─── parse_statement facade ───────────────────────────────────────────────────

class TestParseStatementFacade:
    def test_ofx_detected(self, tmp_path):
        from src.finance.statement_parser import parse_statement
        f = tmp_path / "extrato.ofx"
        f.write_text(_OFX_SAMPLE, encoding="utf-8")
        result = parse_statement(f)
        assert result.format_detected == "ofx_sgml"

    def test_csv_detected(self, tmp_path):
        from src.finance.statement_parser import parse_statement
        f = tmp_path / "extrato.csv"
        f.write_text(_CSV_SAMPLE, encoding="utf-8")
        result = parse_statement(f)
        assert result.format_detected == "csv"


# ─── FinanceStore ─────────────────────────────────────────────────────────────

class TestFinanceStore:
    def test_save_and_get_account(self, tmp_path):
        from src.finance.store import FinanceStore
        from src.finance.account import Account, AccountType
        import time
        store = FinanceStore(tmp_path / "fin.db")
        acc = Account(id="acc1", name="CC", bank_name="Bradesco",
                      account_type=AccountType.CORRENTE, balance_brl=1000.0,
                      updated_at=time.time())
        store.save_account(acc)
        got = store.get_account("acc1")
        assert got is not None
        assert got.bank_name == "Bradesco"

    def test_list_accounts(self, tmp_path):
        from src.finance.store import FinanceStore
        from src.finance.account import Account, AccountType
        import time
        store = FinanceStore(tmp_path / "fin.db")
        for i in range(3):
            store.save_account(Account(id=f"a{i}", name=f"C{i}", bank_name="BB",
                                       account_type=AccountType.CORRENTE,
                                       updated_at=time.time()))
        assert len(store.list_accounts()) == 3

    def test_save_transactions_deduplication(self, tmp_path):
        from src.finance.store import FinanceStore
        from src.finance.account import Transaction, TransactionCategory
        store = FinanceStore(tmp_path / "fin.db")
        t = Transaction(id="t1", account_id="acc1", date=date(2026, 11, 1),
                        description="X", value_brl=-100.0,
                        category=TransactionCategory.OUTROS)
        n1 = store.save_transactions([t])
        n2 = store.save_transactions([t])  # duplicata
        assert n1 == 1
        assert n2 == 0  # ignorada

    def test_totals_by_category(self, tmp_path):
        from src.finance.store import FinanceStore
        from src.finance.account import Transaction, TransactionCategory
        store = FinanceStore(tmp_path / "fin.db")
        txns = [
            Transaction(id="t1", account_id="acc1", date=date(2026, 11, 5),
                        description="Gasolina", value_brl=-200.0,
                        category=TransactionCategory.COMBUSTIVEL),
            Transaction(id="t2", account_id="acc1", date=date(2026, 11, 10),
                        description="Serviço", value_brl=1500.0,
                        category=TransactionCategory.RECEITA_SERVICO),
        ]
        store.save_transactions(txns)
        totals = store.totals_by_category("acc1")
        assert totals["combustivel"] == -200.0
        assert totals["receita_servico"] == 1500.0

    def test_get_balance(self, tmp_path):
        from src.finance.store import FinanceStore
        from src.finance.account import Transaction, TransactionCategory
        store = FinanceStore(tmp_path / "fin.db")
        txns = [
            Transaction(id="t1", account_id="acc1", date=date(2026, 11, 1),
                        description="X", value_brl=5000.0,
                        category=TransactionCategory.RECEITA_SERVICO),
            Transaction(id="t2", account_id="acc1", date=date(2026, 11, 2),
                        description="Y", value_brl=-1200.0,
                        category=TransactionCategory.ALUGUEL),
        ]
        store.save_transactions(txns)
        balance = store.get_balance("acc1")
        assert abs(balance - 3800.0) < 0.01


# ─── FinanceAnalyzer ──────────────────────────────────────────────────────────

class TestFinanceAnalyzer:
    def _populate(self, tmp_path):
        from src.finance.store import FinanceStore
        from src.finance.account import Account, AccountType, Transaction, TransactionCategory
        import time
        store = FinanceStore(tmp_path / "fin.db")
        acc = Account(id="acc1", name="CC", bank_name="Bradesco",
                      account_type=AccountType.CORRENTE, balance_brl=0.0,
                      updated_at=time.time())
        store.save_account(acc)
        store.save_transactions([
            Transaction(id="t1", account_id="acc1", date=date(2026, 11, 5),
                        description="Gasolina", value_brl=-200.0,
                        category=TransactionCategory.COMBUSTIVEL),
            Transaction(id="t2", account_id="acc1", date=date(2026, 11, 10),
                        description="Serviço", value_brl=3000.0,
                        category=TransactionCategory.RECEITA_SERVICO),
            Transaction(id="t3", account_id="acc1", date=date(2026, 11, 15),
                        description="Aluguel", value_brl=-1000.0,
                        category=TransactionCategory.ALUGUEL),
        ])
        return store

    def test_monthly_summary_no_raw_data(self, tmp_path):
        from src.finance.analyzer import FinanceAnalyzer
        store = self._populate(tmp_path)
        analyzer = FinanceAnalyzer(store=store)
        summary = analyzer.monthly_summary(year=2026, month=11)
        # Texto agregado — OK para o modelo
        assert "Resumo financeiro" in summary
        assert "R$" in summary
        # Nunca expõe número de conta bruto
        assert "acc1" not in summary

    def test_accounts_summary_masks_number(self, tmp_path):
        from src.finance.analyzer import FinanceAnalyzer
        store = self._populate(tmp_path)
        analyzer = FinanceAnalyzer(store=store)
        text = analyzer.accounts_summary()
        assert "Bradesco" in text
        assert "123456789" not in text  # número completo nunca exposto

    def test_spending_alerts_no_data(self, tmp_path):
        from src.finance.analyzer import FinanceAnalyzer
        from src.finance.store import FinanceStore
        store = FinanceStore(tmp_path / "fin.db")
        analyzer = FinanceAnalyzer(store=store)
        alerts = analyzer.spending_alerts()
        assert isinstance(alerts, list)

    def test_import_ofx_string(self, tmp_path):
        from src.finance.analyzer import FinanceAnalyzer
        from src.finance.store import FinanceStore
        store = FinanceStore(tmp_path / "fin.db")
        analyzer = FinanceAnalyzer(store=store)
        # Escreve OFX em arquivo temporário e importa
        f = tmp_path / "extrato.ofx"
        f.write_text(_OFX_SAMPLE, encoding="utf-8")
        result = analyzer.import_statement(f)
        assert result["ok"] is True
        assert result["imported"] == 2

    def test_import_csv(self, tmp_path):
        from src.finance.analyzer import FinanceAnalyzer
        from src.finance.store import FinanceStore
        store = FinanceStore(tmp_path / "fin.db")
        analyzer = FinanceAnalyzer(store=store)
        f = tmp_path / "extrato.csv"
        f.write_text(_CSV_SAMPLE, encoding="utf-8")
        result = analyzer.import_statement(f)
        assert result["ok"] is True
        assert result["imported"] == 3

    def test_import_then_summary(self, tmp_path):
        from src.finance.analyzer import FinanceAnalyzer
        from src.finance.store import FinanceStore
        store = FinanceStore(tmp_path / "fin.db")
        analyzer = FinanceAnalyzer(store=store)
        f = tmp_path / "extrato.csv"
        f.write_text(_CSV_SAMPLE, encoding="utf-8")
        analyzer.import_statement(f)
        summary = analyzer.monthly_summary(year=2026, month=11)
        assert "R$" in summary

    def test_context_for_orchestrator_safe(self, tmp_path):
        from src.finance.analyzer import FinanceAnalyzer
        store = self._populate(tmp_path)
        analyzer = FinanceAnalyzer(store=store)
        ctx = analyzer.context_for_orchestrator()
        assert isinstance(ctx, str)
        assert len(ctx) > 0
        # Nunca expõe número de conta bruto no contexto
        assert "123456789" not in ctx

    def test_yearly_summary_no_data(self, tmp_path):
        from src.finance.analyzer import FinanceAnalyzer
        from src.finance.store import FinanceStore
        store = FinanceStore(tmp_path / "fin.db")
        analyzer = FinanceAnalyzer(store=store)
        text = analyzer.yearly_summary(year=2026)
        assert "2026" in text
