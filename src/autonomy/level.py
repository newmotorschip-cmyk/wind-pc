"""
Níveis de autonomia da WIND (seção 7 do WIND_MASTER_SPEC.md).

A0 — Só responde. Zero ação.
A1 — Lê e pesquisa. Sem escrita.
A2 — Executa ações reversíveis em ambiente isolado (spikes, testes, análise).
A3 — Altera projetos autorizados com commit e rollback.
A4 — Age fora (mensagens, publicações, compras) com aprovação por operação.

Regras invariantes:
  - A WIND nunca auto-eleva o próprio nível.
  - Subir de nível = proposta da WIND + histórico medido + aprovação do Felipe.
  - Erro grave rebaixa automaticamente para A1.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class AutonomyLevel(str, Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"

    def label(self) -> str:
        return {
            "A0": "A0 — somente responde",
            "A1": "A1 — lê e pesquisa",
            "A2": "A2 — ações reversíveis em ambiente isolado",
            "A3": "A3 — projetos autorizados com rollback",
            "A4": "A4 — ações externas com aprovação por operação",
        }[self.value]

    def numeric(self) -> int:
        return int(self.value[1])

    def allows_read(self) -> bool:
        return self.numeric() >= 1

    def allows_isolated_write(self) -> bool:
        return self.numeric() >= 2

    def allows_project_write(self) -> bool:
        return self.numeric() >= 3

    def allows_external_action(self) -> bool:
        return self.numeric() >= 4


@dataclass
class LevelChange:
    from_level: AutonomyLevel
    to_level: AutonomyLevel
    reason: str
    approved_by: str     # "Felipe" ou "auto_demotion" (rebaixamento automático)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "from": self.from_level.value,
            "to": self.to_level.value,
            "reason": self.reason,
            "approved_by": self.approved_by,
            "timestamp": self.timestamp,
        }


@dataclass
class AutonomyProfile:
    """
    Perfil de autonomia da WIND.
    current_level é o nível global.
    domain_overrides permitem granularidade por domínio (ex: "re_analysis": A2).
    """
    current_level: AutonomyLevel = AutonomyLevel.A1
    domain_overrides: dict[str, str] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)

    def level_for(self, domain: Optional[str] = None) -> AutonomyLevel:
        if domain and domain in self.domain_overrides:
            return AutonomyLevel(self.domain_overrides[domain])
        return self.current_level

    def apply_change(self, change: LevelChange) -> None:
        """Registra uma mudança de nível (nunca chama auto-elevação)."""
        self.current_level = change.to_level
        self.history.append(change.to_dict())

    def demote_on_error(self, reason: str) -> LevelChange:
        """Rebaixa para A1 automaticamente após erro grave."""
        change = LevelChange(
            from_level=self.current_level,
            to_level=AutonomyLevel.A1,
            reason=f"[AUTO DEMOTION] {reason}",
            approved_by="auto_demotion",
        )
        self.apply_change(change)
        return change

    def to_dict(self) -> dict:
        return {
            "current_level": self.current_level.value,
            "domain_overrides": self.domain_overrides,
            "history": self.history,
        }

    @staticmethod
    def from_dict(d: dict) -> "AutonomyProfile":
        return AutonomyProfile(
            current_level=AutonomyLevel(d.get("current_level", "A1")),
            domain_overrides=d.get("domain_overrides", {}),
            history=d.get("history", []),
        )

    @staticmethod
    def load(path: Path) -> "AutonomyProfile":
        if path.exists():
            try:
                return AutonomyProfile.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, KeyError):
                pass
        return AutonomyProfile()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
