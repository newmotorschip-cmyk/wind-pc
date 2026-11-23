"""
ServiceCase — registro de caso de serviço da oficina REPROTECH.
Dados de cliente são class PERSONAL (LGPD): não saem do PC sem anonimização.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CaseStatus(str, Enum):
    OPEN      = "open"
    CLOSED    = "closed"
    ABANDONED = "abandoned"


class CaseResult(str, Enum):
    SUCCESS  = "success"
    PARTIAL  = "partial"
    FAIL     = "fail"
    UNKNOWN  = "unknown"


@dataclass
class VehicleInfo:
    """Dados do veículo — contém PII (placa): nunca enviar a modelo remoto sem anonimizar."""
    placa: str = ""
    vin: str = ""
    marca: str = ""
    modelo: str = ""
    ano: int = 0
    motor: str = ""

    def anonymized(self) -> "VehicleInfo":
        """Remove identificadores pessoais (placa, VIN) para chamadas remotas."""
        return VehicleInfo(
            placa="[REDACTED]",
            vin="[REDACTED]",
            marca=self.marca,
            modelo=self.modelo,
            ano=self.ano,
            motor=self.motor,
        )

    def to_dict(self) -> dict:
        return {
            "placa": self.placa, "vin": self.vin,
            "marca": self.marca, "modelo": self.modelo,
            "ano": self.ano, "motor": self.motor,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VehicleInfo":
        return cls(**{k: d.get(k, "" if k != "ano" else 0) for k in
                      ("placa", "vin", "marca", "modelo", "ano", "motor")})


@dataclass
class EcuInfo:
    fabricante: str = ""
    referencia: str = ""
    versao_sw: str = ""
    hardware: str = ""

    def to_dict(self) -> dict:
        return {
            "fabricante": self.fabricante, "referencia": self.referencia,
            "versao_sw": self.versao_sw, "hardware": self.hardware,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EcuInfo":
        return cls(**{k: d.get(k, "") for k in ("fabricante", "referencia", "versao_sw", "hardware")})


@dataclass
class ServiceCase:
    queixa: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vehicle: VehicleInfo = field(default_factory=VehicleInfo)
    ecu: EcuInfo = field(default_factory=EcuInfo)
    dtcs: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    result: CaseResult = CaseResult.UNKNOWN
    lessons: list[str] = field(default_factory=list)
    time_minutes: int = 0
    cost_brl: float = 0.0
    status: CaseStatus = CaseStatus.OPEN
    file_hashes: list[str] = field(default_factory=list)
    session_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    closed_at: float | None = None

    def add_action(self, description: str, result: str = "") -> None:
        self.actions.append({
            "description": description,
            "result": result,
            "at": time.time(),
        })
        self.updated_at = time.time()

    def close(
        self,
        result: CaseResult,
        what_worked: str = "",
        what_surprised: str = "",
        repeat_next_time: str = "",
    ) -> None:
        self.result = result
        self.status = CaseStatus.CLOSED
        self.closed_at = time.time()
        self.updated_at = time.time()
        for lesson in (what_worked, what_surprised, repeat_next_time):
            if lesson.strip():
                self.lessons.append(lesson.strip())

    def similarity_text(self) -> str:
        """Texto para indexação e busca por similaridade (sem PII)."""
        parts = [
            self.queixa,
            self.vehicle.marca,
            self.vehicle.modelo,
            self.vehicle.motor,
            self.ecu.fabricante,
            self.ecu.referencia,
            " ".join(self.dtcs),
        ]
        return " ".join(p for p in parts if p)

    def summary(self, include_pii: bool = False) -> str:
        v = self.vehicle if include_pii else self.vehicle.anonymized()
        lines = [
            f"Caso [{self.id[:8]}] — {self.status.value.upper()}",
            f"  Veículo: {v.marca} {v.modelo} {v.ano} {v.motor}",
            f"  ECU: {self.ecu.fabricante} {self.ecu.referencia}",
            f"  Queixa: {self.queixa}",
            f"  DTCs: {', '.join(self.dtcs) or 'nenhum'}",
            f"  Resultado: {self.result.value}",
        ]
        if self.lessons:
            lines.append(f"  Lições: {'; '.join(self.lessons[:2])}")
        return "\n".join(lines)
