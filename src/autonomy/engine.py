"""
Motor de decisão da WIND — Fase 8.

Regras invariantes:
  1. Nunca auto-eleva o nível de autonomia.
  2. Decide sozinha SOMENTE SE: risco ≤ máximo do nível, ação reversível (A0-A2),
     confiança ≥ mínima do nível, e permissão existe.
  3. Fora do envelope → recomenda e aguarda aprovação do Felipe.
  4. Erro grave registrado → rebaixa para A1 automaticamente.
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from .decision import DecisionRecord, DecisionStatus, DecisionStore, RiskLevel
from .level import AutonomyLevel, AutonomyProfile, LevelChange


# Configuração do envelope de autonomia por nível
_MAX_RISK: dict[AutonomyLevel, RiskLevel] = {
    AutonomyLevel.A0: RiskLevel.LOW,
    AutonomyLevel.A1: RiskLevel.LOW,
    AutonomyLevel.A2: RiskLevel.MEDIUM,
    AutonomyLevel.A3: RiskLevel.MEDIUM,
    AutonomyLevel.A4: RiskLevel.HIGH,
}

_MIN_CONFIDENCE: dict[AutonomyLevel, float] = {
    AutonomyLevel.A0: 1.0,   # A0 não age
    AutonomyLevel.A1: 1.0,   # A1 não age (só lê/pesquisa)
    AutonomyLevel.A2: 0.80,
    AutonomyLevel.A3: 0.90,
    AutonomyLevel.A4: 0.95,
}

# A0 e A1 nunca agem autonomamente
_CAN_ACT_AUTONOMOUSLY = {
    AutonomyLevel.A0: False,
    AutonomyLevel.A1: False,
    AutonomyLevel.A2: True,
    AutonomyLevel.A3: True,
    AutonomyLevel.A4: False,  # A4 sempre exige aprovação por operação
}


class DecisionEngine:
    def __init__(self, store: DecisionStore, profile: AutonomyProfile) -> None:
        self._store   = store
        self._profile = profile

    @property
    def profile(self) -> AutonomyProfile:
        return self._profile

    def within_envelope(
        self,
        level: AutonomyLevel,
        risk: RiskLevel,
        confidence: float,
        reversible: bool,
    ) -> tuple[bool, str]:
        """
        Verifica se a ação está dentro do envelope de autonomia.
        Retorna (pode_agir, motivo).
        """
        if not _CAN_ACT_AUTONOMOUSLY[level]:
            return False, f"Nível {level.value} não age autonomamente"

        max_risk = _MAX_RISK[level]
        if risk.numeric() > max_risk.numeric():
            return False, f"Risco {risk.value} excede máximo {max_risk.value} para {level.value}"

        min_conf = _MIN_CONFIDENCE[level]
        if confidence < min_conf:
            return False, f"Confiança {confidence:.0%} abaixo do mínimo {min_conf:.0%} para {level.value}"

        # A2 exige reversibilidade
        if level == AutonomyLevel.A2 and not reversible:
            return False, "Nível A2 exige ação reversível"

        return True, "dentro do envelope"

    def evaluate(
        self,
        request: str,
        options: list[str],
        evidence: str,
        risk: RiskLevel,
        reversible: bool,
        confidence: float,
        domain: Optional[str] = None,
        session_id: str = "",
    ) -> DecisionRecord:
        """
        Avalia uma decisão e retorna um DecisionRecord.
        Se dentro do envelope → APPROVED (autônomo).
        Caso contrário → PENDING (aguarda Felipe).
        """
        level = self._profile.level_for(domain)
        can_act, reason = self.within_envelope(level, risk, confidence, reversible)

        # Escolha: sempre a primeira opção (a WIND deve ordenar da melhor para pior)
        chosen = options[0] if options else "nenhuma opção fornecida"

        status = DecisionStatus.APPROVED if can_act else DecisionStatus.PENDING
        approved_by = "" if can_act else ""  # preenchido pelo Felipe ao aprovar

        record = DecisionRecord(
            id=str(uuid.uuid4()),
            request=request,
            options=options,
            evidence=evidence,
            risk=risk,
            reversible=reversible,
            confidence=confidence,
            chosen_option=chosen,
            approved_by=approved_by,
            status=status,
            result=reason if not can_act else "",
            created_at=time.time(),
            session_id=session_id,
            domain=domain or "",
        )
        self._store.save(record)
        return record

    def approve(self, record_id: str, approved_by: str = "Felipe") -> Optional[DecisionRecord]:
        record = self._store.get(record_id)
        if not record or record.status != DecisionStatus.PENDING:
            return None
        record.approved_by = approved_by
        record.status = DecisionStatus.APPROVED
        self._store.save(record)
        return record

    def reject(self, record_id: str, reason: str = "") -> Optional[DecisionRecord]:
        record = self._store.get(record_id)
        if not record:
            return None
        record.status = DecisionStatus.REJECTED
        record.result  = reason
        self._store.save(record)
        return record

    def mark_executed(self, record_id: str, result: str = "") -> Optional[DecisionRecord]:
        record = self._store.get(record_id)
        if not record or record.status != DecisionStatus.APPROVED:
            return None
        record.status      = DecisionStatus.EXECUTED
        record.result      = result
        record.executed_at = time.time()
        self._store.save(record)
        return record

    def mark_reverted(self, record_id: str, reason: str = "") -> Optional[DecisionRecord]:
        record = self._store.get(record_id)
        if not record:
            return None
        record.status = DecisionStatus.REVERTED
        record.result  = reason
        self._store.save(record)
        return record

    def register_error(self, description: str) -> LevelChange:
        """Rebaixa para A1 automaticamente após erro grave."""
        change = self._profile.demote_on_error(description)
        return change

    def pending_summary(self) -> str:
        pending = self._store.list_pending()
        if not pending:
            return "Nenhuma decisão pendente de aprovação."
        lines = [f"Decisões pendentes ({len(pending)}):"]
        for r in pending[:10]:
            lines.append(f"  {r.summary()}")
        return "\n".join(lines)

    def context_for_orchestrator(self) -> str:
        level = self._profile.current_level
        pending = self._store.list_pending()
        lines = [
            f"Nível de autonomia atual: {level.label()}",
        ]
        if pending:
            lines.append(f"Decisões aguardando aprovação do Felipe: {len(pending)}")
        return "\n".join(lines)
