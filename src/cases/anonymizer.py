"""
Anonimizador LGPD para dados de clientes.
Remove PII (placa, VIN, nomes, CPF/CNPJ) antes de enviar a modelos remotos.
"""
from __future__ import annotations

import re


# Padrões de PII automotiva brasileira
_PLACA_MERCOSUL = re.compile(r'\b[A-Z]{3}[0-9][A-Z][0-9]{2}\b', re.IGNORECASE)
_PLACA_ANTIGA   = re.compile(r'\b[A-Z]{3}[-\s]?[0-9]{4}\b', re.IGNORECASE)
_VIN            = re.compile(r'\b[A-HJ-NPR-Z0-9]{17}\b', re.IGNORECASE)
_CPF            = re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')
_CNPJ           = re.compile(r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b')
_FONE           = re.compile(r'\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?)?\d{4}[-\s]?\d{4}\b')


def anonymize_text(text: str) -> str:
    """Remove PII de um texto antes de enviar ao modelo remoto."""
    text = _PLACA_MERCOSUL.sub('[PLACA]', text)
    text = _PLACA_ANTIGA.sub('[PLACA]', text)
    text = _VIN.sub('[VIN]', text)
    text = _CPF.sub('[CPF]', text)
    text = _CNPJ.sub('[CNPJ]', text)
    text = _FONE.sub('[FONE]', text)
    return text


def anonymize_case_for_remote(case_dict: dict) -> dict:
    """
    Recebe o dict de um ServiceCase e retorna versão anonimizada.
    Preserva dados técnicos (ECU, DTCs, queixa) mas remove identificadores de cliente.
    """
    import copy
    d = copy.deepcopy(case_dict)

    # Zera campos PII diretos
    vehicle = d.get("vehicle", {})
    vehicle["placa"] = "[REDACTED]"
    vehicle["vin"]   = "[REDACTED]"
    d["vehicle"] = vehicle

    # Sanitiza texto livre
    if "queixa" in d:
        d["queixa"] = anonymize_text(d["queixa"])
    for action in d.get("actions", []):
        if "description" in action:
            action["description"] = anonymize_text(action["description"])
    d["lessons"] = [anonymize_text(l) for l in d.get("lessons", [])]

    return d
