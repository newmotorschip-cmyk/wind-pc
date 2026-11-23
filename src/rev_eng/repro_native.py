"""
Interfaces para os motores do REPROTECH Native.
Reutiliza (via contrato) os engines já existentes em vez de reimplementar:
  - Fingerprinter ECU
  - Diff ORI×MOD
  - Parsers A2L / DCM / XDF
  - Detector de DTC

Enquanto o REPROTECH Native não estiver acessível por API/CLI definida,
todos os conectores retornam stubs e registram o motivo.

Ativação: definir REPRO_NATIVE_API_URL no ambiente.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


REPRO_NATIVE_API = os.getenv("REPRO_NATIVE_API_URL", "")


@dataclass
class FingerprintResult:
    """Resultado da identificação de ECU pelo fingerprinter."""
    matched: bool
    ecu_id: str = ""
    manufacturer: str = ""
    platform: str = ""
    sw_version: str = ""
    confidence: float = 0.0
    source: str = "stub"
    raw: dict = field(default_factory=dict)


@dataclass
class DiffResult:
    """Resultado do diff entre arquivo ORI e MOD."""
    total_bytes: int = 0
    changed_bytes: int = 0
    changed_regions: list[dict] = field(default_factory=list)  # [{offset, length, ori, mod}]
    source: str = "stub"


@dataclass
class A2LResult:
    """Resultado do parser A2L — extrai características, mapas e parâmetros."""
    measurements: list[dict] = field(default_factory=list)
    characteristics: list[dict] = field(default_factory=list)
    functions: list[dict] = field(default_factory=list)
    source: str = "stub"


@dataclass
class DtcResult:
    """Resultado da detecção de DTCs no binário."""
    dtcs: list[str] = field(default_factory=list)
    table_offset: Optional[int] = None
    source: str = "stub"


class EcuFingerprintConnector(ABC):
    @abstractmethod
    def fingerprint(self, binary_data: bytes) -> FingerprintResult: ...
    @abstractmethod
    def is_available(self) -> bool: ...


class DiffConnector(ABC):
    @abstractmethod
    def diff(self, ori_data: bytes, mod_data: bytes) -> DiffResult: ...
    @abstractmethod
    def is_available(self) -> bool: ...


class A2LParserConnector(ABC):
    @abstractmethod
    def parse(self, a2l_path: str) -> A2LResult: ...
    @abstractmethod
    def is_available(self) -> bool: ...


class DtcDetectorConnector(ABC):
    @abstractmethod
    def detect(self, binary_data: bytes, arch: str = "") -> DtcResult: ...
    @abstractmethod
    def is_available(self) -> bool: ...


# ── Stubs (ativos enquanto REPROTECH Native não está conectado) ───────────────

class EcuFingerprintStub(EcuFingerprintConnector):
    def fingerprint(self, binary_data: bytes) -> FingerprintResult:
        return FingerprintResult(matched=False, source="stub — REPRO_NATIVE_API_URL não configurada")

    def is_available(self) -> bool:
        return False


class DiffStub(DiffConnector):
    def diff(self, ori_data: bytes, mod_data: bytes) -> DiffResult:
        # Implementação básica sem o engine real
        changed = sum(1 for a, b in zip(ori_data, mod_data) if a != b)
        length = max(len(ori_data), len(mod_data))
        return DiffResult(
            total_bytes=length,
            changed_bytes=changed,
            changed_regions=[],
            source="stub-builtin (sem identificação de regiões)",
        )

    def is_available(self) -> bool:
        return True  # stub built-in sempre disponível


class A2LParserStub(A2LParserConnector):
    def parse(self, a2l_path: str) -> A2LResult:
        return A2LResult(source="stub — REPRO_NATIVE_API_URL não configurada")

    def is_available(self) -> bool:
        return False


class DtcDetectorStub(DtcDetectorConnector):
    def detect(self, binary_data: bytes, arch: str = "") -> DtcResult:
        # Busca ingênua por padrões DTC P/B/C/U + 4 hex digits em ASCII no binário
        import re
        text = binary_data.decode("latin-1", errors="replace")
        raw = re.findall(r'\b[PBCU][0-9A-Fa-f]{4}\b', text)
        return DtcResult(dtcs=sorted(set(raw)), source="stub-builtin (regex em ASCII)")

    def is_available(self) -> bool:
        return True


# ── Factory — retorna conector real se disponível, stub caso contrário ─────────

class ReproNativeConnectors:
    """Ponto de acesso centralizado para os engines do REPROTECH Native."""

    def __init__(self, api_url: str = REPRO_NATIVE_API) -> None:
        self._api_url = api_url

    @property
    def fingerprint(self) -> EcuFingerprintConnector:
        # TODO: retornar HTTP connector quando REPRO_NATIVE_API_URL configurada
        return EcuFingerprintStub()

    @property
    def diff(self) -> DiffConnector:
        return DiffStub()

    @property
    def a2l(self) -> A2LParserConnector:
        return A2LParserStub()

    @property
    def dtc(self) -> DtcDetectorConnector:
        return DtcDetectorStub()

    def status(self) -> dict:
        return {
            "api_url": self._api_url or "não configurada",
            "fingerprint": self.fingerprint.is_available(),
            "diff": self.diff.is_available(),
            "a2l": self.a2l.is_available(),
            "dtc": self.dtc.is_available(),
        }
