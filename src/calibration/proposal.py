"""
CalibrationProposal — estrutura de proposta de calibração com fluxo de aprovação.
Toda alteração de mapa exige: backup verificado, checksum válido, aprovação explícita.
A WIND propõe; Felipe aprova; a gravação NUNCA ocorre sem aprovação por operação.
"""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProposalStatus(str, Enum):
    DRAFT    = "draft"
    PENDING  = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED  = "applied"
    REVERTED = "reverted"


@dataclass
class MapDelta:
    map_name: str
    description: str
    unit: str
    original_values: list[float]
    proposed_values: list[float]
    axis_labels: list[str] = field(default_factory=list)
    max_delta_percent: float = 0.0
    safety_limits: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.original_values and self.proposed_values:
            diffs = [abs(p - o) / (abs(o) + 1e-9) * 100
                     for o, p in zip(self.original_values, self.proposed_values)]
            self.max_delta_percent = max(diffs) if diffs else 0.0

    def to_dict(self) -> dict:
        return {
            "map_name": self.map_name,
            "description": self.description,
            "unit": self.unit,
            "original_values": self.original_values,
            "proposed_values": self.proposed_values,
            "axis_labels": self.axis_labels,
            "max_delta_percent": self.max_delta_percent,
            "safety_limits": self.safety_limits,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MapDelta":
        obj = cls(
            map_name=d["map_name"],
            description=d["description"],
            unit=d["unit"],
            original_values=d["original_values"],
            proposed_values=d["proposed_values"],
            axis_labels=d.get("axis_labels", []),
            safety_limits=d.get("safety_limits", {}),
        )
        obj.max_delta_percent = d.get("max_delta_percent", obj.max_delta_percent)
        return obj


@dataclass
class CalibrationProposal:
    id: str
    ecu_family_id: str
    vehicle_description: str
    maps: list[MapDelta]
    justification: str
    validation_plan: str
    guardian_level: int
    requires_legal_note: bool
    legal_note: str
    status: ProposalStatus
    created_at: float
    session_id: str
    original_file_hash: str = ""
    approved_by: str = ""
    approved_at: float = 0.0
    rejection_reason: str = ""
    applied_at: float = 0.0

    @property
    def map_names(self) -> list[str]:
        return [m.map_name for m in self.maps]

    @property
    def max_delta_percent(self) -> float:
        return max((m.max_delta_percent for m in self.maps), default=0.0)

    def summary(self) -> str:
        legal_warn = "\n  ⚠️  REQUER NOTA LEGAL — ver legal_note" if self.requires_legal_note else ""
        lines = [
            f"=== Proposta [{self.id[:8]}] ===",
            f"Status: {self.status.value}",
            f"ECU: {self.ecu_family_id}  Veículo: {self.vehicle_description}",
            f"Mapas ({len(self.maps)}):",
        ]
        for m in self.maps:
            lines.append(f"  · {m.map_name} ({m.unit}) — delta máx: {m.max_delta_percent:.1f}%")
        lines += [
            f"Nível Guardian: {self.guardian_level}{legal_warn}",
            f"Justificativa: {self.justification}",
            f"Validação: {self.validation_plan}",
        ]
        if self.status == ProposalStatus.APPROVED:
            lines.append(f"Aprovado por: {self.approved_by}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ecu_family_id": self.ecu_family_id,
            "vehicle_description": self.vehicle_description,
            "maps": [m.to_dict() for m in self.maps],
            "justification": self.justification,
            "validation_plan": self.validation_plan,
            "guardian_level": self.guardian_level,
            "requires_legal_note": self.requires_legal_note,
            "legal_note": self.legal_note,
            "status": self.status.value,
            "created_at": self.created_at,
            "session_id": self.session_id,
            "original_file_hash": self.original_file_hash,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "rejection_reason": self.rejection_reason,
            "applied_at": self.applied_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CalibrationProposal":
        return cls(
            id=d["id"],
            ecu_family_id=d["ecu_family_id"],
            vehicle_description=d["vehicle_description"],
            maps=[MapDelta.from_dict(m) for m in d.get("maps", [])],
            justification=d["justification"],
            validation_plan=d["validation_plan"],
            guardian_level=d["guardian_level"],
            requires_legal_note=d["requires_legal_note"],
            legal_note=d.get("legal_note", ""),
            status=ProposalStatus(d["status"]),
            created_at=d["created_at"],
            session_id=d.get("session_id", ""),
            original_file_hash=d.get("original_file_hash", ""),
            approved_by=d.get("approved_by", ""),
            approved_at=d.get("approved_at", 0.0),
            rejection_reason=d.get("rejection_reason", ""),
            applied_at=d.get("applied_at", 0.0),
        )
