"""
Analisador financeiro da WIND — Fase 7 (somente leitura).

IMPORTANTE — Guardian:
  - Este módulo NUNCA envia dados financeiros brutos a modelos remotos.
  - Os métodos retornam textos agregados (totais, categorias) — estes SIM
    podem ser injetados no contexto do modelo como texto público.
  - Dados brutos (transações, números de conta) ficam no SQLite local.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Optional

from .account import Account, TransactionCategory
from .store import FinanceStore
from .statement_parser import ParseResult, parse_statement
from pathlib import Path


# Categorias de receita vs despesa
_RECEITA = {TransactionCategory.RECEITA_SERVICO, TransactionCategory.RECEITA_VENDA}
_DESPESA = {
    TransactionCategory.COMBUSTIVEL, TransactionCategory.PECAS,
    TransactionCategory.FERRAMENTAS, TransactionCategory.FORNECEDOR,
    TransactionCategory.FOLHA_PAGAMENTO, TransactionCategory.IMPOSTOS,
    TransactionCategory.ALUGUEL, TransactionCategory.SERVICOS_UTIL,
}

_CATEGORY_LABELS: dict[str, str] = {
    "combustivel":        "Combustível",
    "pecas":              "Peças",
    "ferramentas":        "Ferramentas",
    "fornecedor":         "Fornecedores",
    "folha_pagamento":    "Folha de pagamento",
    "impostos":           "Impostos/taxas",
    "aluguel":            "Aluguel",
    "servicos_utilidades":"Serviços/utilidades",
    "receita_servico":    "Receita serviços",
    "receita_venda":      "Receita vendas",
    "transferencia":      "Transferências",
    "corretora":          "Corretora/investimentos",
    "outros":             "Outros",
}


class FinanceAnalyzer:
    """
    Análise somente leitura. Nunca registra transações — apenas consulta.
    Para importar extratos use import_statement().
    """

    def __init__(self, store: Optional[FinanceStore] = None, db_path: Optional[Path] = None) -> None:
        self._store = store or FinanceStore(db_path or Path("data/wind.db"))

    # ── Import ────────────────────────────────────────────────────────────────

    def import_statement(self, path: Path | str) -> dict:
        """
        Importa extrato (OFX ou CSV) para o SQLite local.
        Retorna resumo sem dados brutos para ser exibido ao usuário.
        """
        result: ParseResult = parse_statement(path)
        if not result.ok:
            return {"ok": False, "errors": result.errors, "imported": 0}

        # Persistir conta se detectada
        if result.account:
            existing = self._store.get_account(result.account.id)
            if not existing:
                self._store.save_account(result.account)

        inserted = self._store.save_transactions(result.transactions)

        return {
            "ok": True,
            "format": result.format_detected,
            "total_transactions": len(result.transactions),
            "imported": inserted,
            "skipped": len(result.transactions) - inserted,
            "errors": result.errors,
            "account_id": result.account.id if result.account else None,
        }

    # ── Summary ───────────────────────────────────────────────────────────────

    def monthly_summary(self, account_id: Optional[str] = None,
                         year: Optional[int] = None, month: Optional[int] = None) -> str:
        """
        Retorna texto agregado seguro para injetar no contexto do modelo.
        Nunca inclui números de conta, transações individuais ou dados brutos.
        """
        today = date.today()
        y = year  or today.year
        m = month or today.month
        start = date(y, m, 1)
        _, last_day = monthrange(y, m)
        end = date(y, m, last_day)

        totals = self._store.totals_by_category(account_id, start, end)
        txns   = self._store.list_transactions(account_id, start, end, limit=1000)

        total_receita = sum(v for cat, v in totals.items()
                            if TransactionCategory(cat) in _RECEITA and v > 0)
        total_despesa = sum(abs(v) for cat, v in totals.items()
                            if TransactionCategory(cat) in _DESPESA and v < 0)
        saldo_mes = sum(totals.values())

        lines = [f"=== Resumo financeiro {m:02d}/{y} ==="]
        lines.append(f"Receita total:  R$ {total_receita:>12,.2f}")
        lines.append(f"Despesa total:  R$ {total_despesa:>12,.2f}")
        lines.append(f"Saldo do mês:   R$ {saldo_mes:>12,.2f}")
        lines.append(f"Transações:     {len(txns)}")
        lines.append("")
        lines.append("Por categoria:")
        for cat, total in sorted(totals.items(), key=lambda x: abs(x[1]), reverse=True):
            if total == 0:
                continue
            label = _CATEGORY_LABELS.get(cat, cat)
            lines.append(f"  {label:<30s} R$ {total:>12,.2f}")

        return "\n".join(lines)

    def spending_alerts(self, account_id: Optional[str] = None) -> list[str]:
        """
        Detecta padrões anômalos e gera lista de alertas em texto.
        Texto agregado — seguro para o modelo.
        """
        alerts: list[str] = []
        today = date.today()

        # Mês atual vs mês anterior
        this_start  = date(today.year, today.month, 1)
        prev_month  = (this_start - timedelta(days=1))
        prev_start  = date(prev_month.year, prev_month.month, 1)
        _, last_day = monthrange(prev_month.year, prev_month.month)
        prev_end    = date(prev_month.year, prev_month.month, last_day)

        curr_totals = self._store.totals_by_category(account_id, this_start, today)
        prev_totals = self._store.totals_by_category(account_id, prev_start, prev_end)

        for cat, curr_val in curr_totals.items():
            if curr_val >= 0:
                continue  # só alertas de despesa
            prev_val = prev_totals.get(cat, 0.0)
            if prev_val == 0:
                continue
            pct_change = abs(curr_val) / abs(prev_val) - 1
            label = _CATEGORY_LABELS.get(cat, cat)
            if pct_change > 0.3:
                alerts.append(
                    f"⚠️  {label}: +{pct_change:.0%} vs mês anterior "
                    f"(R$ {abs(curr_val):,.0f} vs R$ {abs(prev_val):,.0f})"
                )

        # Saldo negativo
        all_txns = self._store.list_transactions(account_id, limit=1000)
        balance = sum(t.value_brl for t in all_txns)
        if balance < 0:
            alerts.append(f"🚨 Saldo consolidado negativo: R$ {balance:,.2f}")

        return alerts

    def accounts_summary(self) -> str:
        """Resumo de contas (nome do banco + saldo) — sem número de conta."""
        accounts = self._store.list_accounts()
        if not accounts:
            return "Nenhuma conta cadastrada. Use /financas-importar para importar um extrato."
        lines = [f"Contas cadastradas ({len(accounts)}):"]
        total = 0.0
        for acc in accounts:
            balance = self._store.get_balance(acc.id)
            # Atualiza saldo calculado
            lines.append(f"  {acc.bank_name} {acc.name} ({acc.account_type.value}): R$ {balance:,.2f}")
            total += balance
        lines.append(f"\nSaldo consolidado: R$ {total:,.2f}")
        return "\n".join(lines)

    def context_for_orchestrator(self) -> str:
        """
        Texto agregado para injetar no prompt do modelo quando o Felipe perguntar
        sobre finanças. Nunca inclui dados brutos.
        """
        summary = self.accounts_summary()
        alerts  = self.spending_alerts()
        parts   = [summary]
        if alerts:
            parts.append("\nAlertas financeiros:")
            parts.extend(f"  {a}" for a in alerts)
        return "\n".join(parts)

    def yearly_summary(self, account_id: Optional[str] = None, year: Optional[int] = None) -> str:
        y = year or date.today().year
        monthly = self._store.monthly_totals(account_id, year=y)
        if not monthly:
            return f"Sem dados para {y}."
        lines = [f"=== Resumo anual {y} ==="]
        annual_total = 0.0
        for row in monthly:
            lines.append(f"  {row['month']}: R$ {row['total']:,.2f}")
            annual_total += row["total"]
        lines.append(f"\nTotal {y}: R$ {annual_total:,.2f}")
        return "\n".join(lines)
