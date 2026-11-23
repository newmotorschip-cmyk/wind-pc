"""
Classificador de dados — Guardian mínimo da Fase 1.
Categorias: public | personal | confidential_client | financial | secret
"""
from __future__ import annotations

import re
from enum import Enum


class DataClass(Enum):
    PUBLIC = "public"
    PERSONAL = "personal"
    CONFIDENTIAL_CLIENT = "confidential_client"
    FINANCIAL = "financial"
    SECRET = "secret"


# Padrões por classe (regras simples, complementar com ML na Fase 8)
_SECRET_PATTERNS = [
    r"(?i)(api[_\s]?key|api[_\s]?secret|private[_\s]?key|secret[_\s]?key)",
    r"(?i)(anthropic|openai|sk-ant-|sk-)[a-zA-Z0-9\-]{10,}",
    r"(?i)(password|senha|pw)\s*[:=]\s*\S+",
    r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----",
    r"(?i)ssh-rsa\s+[A-Za-z0-9+/]{30,}",
    r"(?i)(token|bearer)\s*[:=]\s*[a-zA-Z0-9\-_.]{20,}",
    r"(?i)ANTHROPIC_API_KEY|OPENAI_API_KEY",
]

_FINANCIAL_PATTERNS = [
    r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",   # CPF
    r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",  # CNPJ
    r"(?i)(conta\s+corrente|conta\s+poupança|agência)\s*\d",
    r"(?i)(pix|ted|doc|transferência).*R\$",
    r"(?i)(corretora|exchange|investimento|carteira|saldo)",
]

_PERSONAL_PATTERNS = [
    r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",   # nome próprio (heurística fraca)
    r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",   # CPF
    r"\b[A-Z]{3}-\d{4}\b|\b[A-Z]{3}\d[A-Z]\d{2}\b",  # placa veicular
    r"(?i)\b(vin|chassis)\s*[:=]?\s*[A-HJ-NPR-Z0-9]{17}\b",
    r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b",  # email
    r"(?i)(telefone|celular|whatsapp)\s*[:=]?\s*\+?[\d\s\-\(\)]{9,}",
]

_CLIENT_KEYWORDS = [
    "cliente",
    "veículo do cliente",
    "proprietário",
    "dono do carro",
    "nome do cliente",
]


def classify(text: str) -> DataClass:
    """Classifica o dado mais sensível presente no texto."""
    for pattern in _SECRET_PATTERNS:
        if re.search(pattern, text):
            return DataClass.SECRET
    for pattern in _FINANCIAL_PATTERNS:
        if re.search(pattern, text):
            return DataClass.FINANCIAL
    for kw in _CLIENT_KEYWORDS:
        if kw.lower() in text.lower():
            return DataClass.CONFIDENTIAL_CLIENT
    for pattern in _PERSONAL_PATTERNS:
        if re.search(pattern, text):
            return DataClass.PERSONAL
    return DataClass.PUBLIC


def classify_batch(texts: list[str]) -> DataClass:
    """Classifica o mais sensível de uma lista de textos."""
    priority = [
        DataClass.SECRET,
        DataClass.FINANCIAL,
        DataClass.CONFIDENTIAL_CLIENT,
        DataClass.PERSONAL,
        DataClass.PUBLIC,
    ]
    classes = [classify(t) for t in texts]
    for dc in priority:
        if dc in classes:
            return dc
    return DataClass.PUBLIC
