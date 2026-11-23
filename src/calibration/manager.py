"""
CalibrationManager — cria, gerencia e aprova propostas de calibração.
Regras de segurança:
  - Propostas Guardian ≥ 4 exigem legal_note preenchida.
  - Aprovação registrada; gravação real NUNCA ocorre aqui (sem hardware real).
  - Fluxo: criar → aprovar → (Felipe grava) → mark_applied.
"""
from __future__ import annotations
import time
import uuid
from typing import Optional

from .ecu_families import EcuFamily, get_family, list_families, search_families
from .map_taxonomy import MapCategory, MapDefinition, list_maps, guardian_level_for_map
from .proposal import CalibrationProposal, MapDelta, ProposalStatus
from .checksum import ChecksumVerifier, ChecksumResult
from .store import CalibrationStore


class CalibrationError(Exception):
    pass


class CalibrationManager:
    def __init__(self, store: CalibrationStore) -> None:
        self._store = store
        self._checksum = ChecksumVerifier()

    # ── Famílias ──────────────────────────────────────────────────────────────

    def families(self) -> list[EcuFamily]:
        return list_families()

    def find_family(self, query: str) -> Optional[EcuFamily]:
        results = search_families(query)
        if not results:
            return None
        exact = next((f for f in results if query.lower() == f.id.lower()), None)
        return exact or results[0]

    # ── Taxonomia de mapas ────────────────────────────────────────────────────

    def maps_for_category(self, category: MapCategory) -> list[MapDefinition]:
        return list_maps(category)

    def all_maps(self) -> list[MapDefinition]:
        return list_maps()

    # ── Propostas ─────────────────────────────────────────────────────────────

    def create_proposal(
        self,
        ecu_family_id: str,
        vehicle_description: str,
        maps: list[MapDelta],
        justification: str,
        validation_plan: str,
        legal_note: str = "",
        session_id: str = "",
        original_file_hash: str = "",
    ) -> CalibrationProposal:
        guardian_level = max(
            (guardian_level_for_map(m.map_name) for m in maps),
            default=2,
        )
        requires_legal = guardian_level >= 4

        if requires_legal and not legal_note:
            raise CalibrationError(
                "Proposta inclui mapas de nível legal (emissões/imobilizador/odômetro). "
                "Preencha legal_note com autorização do titular e justificativa legal."
            )

        proposal = CalibrationProposal(
            id=str(uuid.uuid4()),
            ecu_family_id=ecu_family_id,
            vehicle_description=vehicle_description,
            maps=maps,
            justification=justification,
            validation_plan=validation_plan,
            guardian_level=guardian_level,
            requires_legal_note=requires_legal,
            legal_note=legal_note,
            status=ProposalStatus.PENDING,
            created_at=time.time(),
            session_id=session_id,
            original_file_hash=original_file_hash,
        )
        self._store.save(proposal)
        return proposal

    def approve(self, proposal_id: str, approved_by: str = "Felipe") -> CalibrationProposal:
        """Registra aprovação. NÃO executa gravação — apenas o registro."""
        p = self._store.get(proposal_id)
        if not p:
            raise CalibrationError(f"Proposta {proposal_id} não encontrada.")
        if p.status not in (ProposalStatus.PENDING, ProposalStatus.DRAFT):
            raise CalibrationError(
                f"Proposta está em status '{p.status.value}', não pode ser aprovada."
            )
        p.status = ProposalStatus.APPROVED
        p.approved_by = approved_by
        p.approved_at = time.time()
        self._store.save(p)
        return p

    def reject(self, proposal_id: str, reason: str) -> CalibrationProposal:
        p = self._store.get(proposal_id)
        if not p:
            raise CalibrationError(f"Proposta {proposal_id} não encontrada.")
        p.status = ProposalStatus.REJECTED
        p.rejection_reason = reason
        self._store.save(p)
        return p

    def mark_applied(self, proposal_id: str) -> CalibrationProposal:
        """Registra que a gravação foi feita pelo Felipe. WIND não executa isso."""
        p = self._store.get(proposal_id)
        if not p:
            raise CalibrationError(f"Proposta {proposal_id} não encontrada.")
        if p.status != ProposalStatus.APPROVED:
            raise CalibrationError(
                "Só propostas aprovadas podem ser marcadas como aplicadas. "
                "Fluxo: criar → aprovar → aplicar."
            )
        p.status = ProposalStatus.APPLIED
        p.applied_at = time.time()
        self._store.save(p)
        return p

    def verify_checksum(self, data: bytes, family_id: str) -> ChecksumResult:
        return self._checksum.verify(data, family_id)

    def list_pending(self) -> list[CalibrationProposal]:
        return self._store.list_pending()

    def list_all(self) -> list[CalibrationProposal]:
        return self._store.list_all()

    def get(self, proposal_id: str) -> Optional[CalibrationProposal]:
        return self._store.get(proposal_id)

    def context_for_ecu(self, family_id: str) -> str:
        """Bloco de contexto para injeção no sistema."""
        family = get_family(family_id)
        proposals = self._store.list_by_ecu(family_id)
        lines = []
        if family:
            lines.append(f"[Família ECU: {family.manufacturer} {family.series}]")
            lines.append(f"  Arquiteturas: {', '.join(family.architectures)}")
            lines.append(f"  Boot: {', '.join(family.boot_modes)}")
        if proposals:
            lines.append(f"\n[Propostas anteriores para {family_id}: {len(proposals)}]")
            for p in proposals[:3]:
                lines.append(f"  [{p.id[:8]}] {p.status.value} — {', '.join(p.map_names[:3])}")
        return "\n".join(lines) if lines else ""
