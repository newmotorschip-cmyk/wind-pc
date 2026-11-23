"""
Modelos de dados financeiros da WIND — Fase 7 (somente leitura).

Classe Guardian: FINANCEIRO
  - Dados brutos ficam no PC / SQLite local.
  - Nunca serializar Transaction.raw_memo ou Account.account_number em prompts de modelo.
  - Somente textos agregados (totais, categorias) podem ir ao modelo.
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class TransactionCategory(str, Enum):
    COMBUSTIVEL     = "combustivel"
    PECAS           = "pecas"
    FERRAMENTAS     = "ferramentas"
    FORNECEDOR      = "fornecedor"
    FOLHA_PAGAMENTO = "folha_pagamento"
    IMPOSTOS        = "impostos"
    ALUGUEL         = "aluguel"
    SERVICOS_UTIL   = "servicos_utilidades"
    RECEITA_SERVICO = "receita_servico"
    RECEITA_VENDA   = "receita_venda"
    TRANSFERENCIA   = "transferencia"
    CORRETORA       = "corretora"
    OUTROS          = "outros"


_CATEGORY_KEYWORDS: dict[TransactionCategory, list[str]] = {
    TransactionCategory.COMBUSTIVEL:     ["combustivel", "posto", "petrobras", "ipiranga", "shell", "gasolina", "diesel", "etanol"],
    TransactionCategory.PECAS:           ["autopeca", "rolamento", "filtro", "correia", "amortecedor"],
    TransactionCategory.FERRAMENTAS:     ["ferramenta", "snap-on", "gedore", "makita", "dewalt"],
    TransactionCategory.FORNECEDOR:      ["fornecedor", "distribuidora", "atacado", "nota fiscal", "nf-e"],
    TransactionCategory.FOLHA_PAGAMENTO: ["salario", "folha", "clt", "funcionario", "rescisao", "ferias"],
    TransactionCategory.IMPOSTOS:        ["simples nacional", "cofins", "irpj", "csll", "receita federal", "das "],
    TransactionCategory.ALUGUEL:         ["aluguel", "locacao", "locação", "iptu", "condominio"],
    TransactionCategory.CORRETORA:       ["xp investimentos", "rico ", "clear ", "nuinvest", "b3 ", "cdb ", "cdb-", "lci ", "lca ", "tesouro direto", "nubank invest"],
    TransactionCategory.SERVICOS_UTIL:   ["energia eletrica", "conta de agua", "esgoto", "copel", "sanepar", "telecom", "internet ", "telefone", "claro ", "vivo ", "tim "],
    TransactionCategory.RECEITA_SERVICO: ["servico prestado", "mao de obra", "revisao", "diagnose", "reparo", "ord.serv"],
    TransactionCategory.RECEITA_VENDA:   ["venda de", "nf venda"],
    TransactionCategory.TRANSFERENCIA:   ["transferencia", "credito em conta"],
    TransactionCategory.OUTROS:          [],
}

# Palavras-chave exatas (correspondência de palavra inteira) para evitar falsos positivos
_WHOLE_WORD_KEYWORDS: dict[TransactionCategory, list[str]] = {
    TransactionCategory.IMPOSTOS:        ["das", "pis", "iss", "icms"],
    TransactionCategory.CORRETORA:       ["xp", "b3", "cdb", "lci", "lca", "fii"],
    TransactionCategory.TRANSFERENCIA:   ["ted", "pix", "doc"],
    TransactionCategory.SERVICOS_UTIL:   ["tim", "vivo", "claro", "copel"],
}


def categorize(description: str) -> TransactionCategory:
    lower = description.lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if cat == TransactionCategory.OUTROS:
            continue
        if any(kw in lower for kw in keywords):
            return cat
    # Segunda passagem: palavras-chave de palavra inteira
    for cat, keywords in _WHOLE_WORD_KEYWORDS.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                return cat
    return TransactionCategory.OUTROS


@dataclass
class Transaction:
    """
    Dados de classe FINANCEIRO — nunca enviar raw_memo ou description a modelos remotos.
    """
    id: str
    account_id: str
    date: date
    description: str       # classe financeiro — não vai ao modelo
    value_brl: float       # positivo = crédito, negativo = débito
    category: TransactionCategory
    raw_memo: str = ""     # classe financeiro — nunca ao modelo
    source_file: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "account_id": self.account_id,
            "date": self.date.isoformat(),
            "description": self.description,
            "value_brl": self.value_brl,
            "category": self.category.value,
            "raw_memo": self.raw_memo,
            "source_file": self.source_file,
        }

    @staticmethod
    def from_dict(d: dict) -> "Transaction":
        return Transaction(
            id=d["id"],
            account_id=d["account_id"],
            date=date.fromisoformat(d["date"]),
            description=d["description"],
            value_brl=float(d["value_brl"]),
            category=TransactionCategory(d["category"]),
            raw_memo=d.get("raw_memo", ""),
            source_file=d.get("source_file", ""),
        )

    @staticmethod
    def make_id(account_id: str, dt: date, description: str, value: float) -> str:
        raw = f"{account_id}|{dt.isoformat()}|{description}|{value:.2f}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class AccountType(str, Enum):
    CORRENTE     = "corrente"
    POUPANCA     = "poupanca"
    INVESTIMENTO = "investimento"
    CARTAO       = "cartao"
    OUTRO        = "outro"


@dataclass
class Account:
    """
    Dados de classe FINANCEIRO.
    account_number é mascarado (últimos 4 dígitos) ao exibir.
    """
    id: str
    name: str
    bank_name: str
    account_type: AccountType
    agency: str = ""
    account_number: str = ""   # classe financeiro — mascarar ao exibir
    balance_brl: float = 0.0
    updated_at: float = field(default_factory=time.time)
    currency: str = "BRL"
    active: bool = True

    def masked_number(self) -> str:
        if len(self.account_number) >= 4:
            return "****" + self.account_number[-4:]
        return "****"

    def summary_line(self) -> str:
        return (
            f"[{self.id[:8]}] {self.bank_name} {self.name} "
            f"({self.account_type.value}) {self.masked_number()} "
            f"R$ {self.balance_brl:,.2f}"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "bank_name": self.bank_name,
            "account_type": self.account_type.value,
            "agency": self.agency,
            "account_number": self.account_number,
            "balance_brl": self.balance_brl,
            "updated_at": self.updated_at,
            "currency": self.currency,
            "active": self.active,
        }

    @staticmethod
    def from_dict(d: dict) -> "Account":
        return Account(
            id=d["id"],
            name=d["name"],
            bank_name=d["bank_name"],
            account_type=AccountType(d.get("account_type", "outro")),
            agency=d.get("agency", ""),
            account_number=d.get("account_number", ""),
            balance_brl=float(d.get("balance_brl", 0.0)),
            updated_at=float(d.get("updated_at", 0.0)),
            currency=d.get("currency", "BRL"),
            active=bool(d.get("active", True)),
        )
