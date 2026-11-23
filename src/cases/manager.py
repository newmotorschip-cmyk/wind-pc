"""
CaseManager — abre, fecha e recupera casos de serviço.
Encapsula o fluxo de fechamento (3 perguntas) e a busca por similaridade.
"""
from __future__ import annotations

from typing import Optional

from .case import CaseResult, CaseStatus, EcuInfo, ServiceCase, VehicleInfo
from .store import CaseStore


CLOSING_QUESTIONS = [
    "O que funcionou neste serviço? (pode deixar em branco)",
    "O que te surpreendeu ou foi diferente do esperado? (pode deixar em branco)",
    "O que repetir da próxima vez com este tipo de caso? (pode deixar em branco)",
]


class CaseManager:
    def __init__(self, store: CaseStore | None = None) -> None:
        self._store = store or CaseStore()

    def open(
        self,
        queixa: str,
        vehicle: VehicleInfo | None = None,
        ecu: EcuInfo | None = None,
        dtcs: list[str] | None = None,
        session_id: str = "",
    ) -> ServiceCase:
        """Abre um novo caso de serviço."""
        case = ServiceCase(
            queixa=queixa,
            vehicle=vehicle or VehicleInfo(),
            ecu=ecu or EcuInfo(),
            dtcs=dtcs or [],
            session_id=session_id,
        )
        self._store.save(case)
        return case

    def close(
        self,
        case_id: str,
        result: CaseResult = CaseResult.SUCCESS,
        what_worked: str = "",
        what_surprised: str = "",
        repeat_next_time: str = "",
        time_minutes: int = 0,
        cost_brl: float = 0.0,
    ) -> Optional[ServiceCase]:
        """Fecha um caso com as respostas às 3 perguntas de fechamento."""
        case = self._store.get(case_id)
        if not case:
            return None
        case.close(result, what_worked, what_surprised, repeat_next_time)
        case.time_minutes = time_minutes
        case.cost_brl = cost_brl
        self._store.save(case)
        return case

    def find_similar(self, queixa: str, vehicle: VehicleInfo | None = None, ecu: EcuInfo | None = None, limit: int = 3) -> list[ServiceCase]:
        """
        Recupera casos similares por veículo/ECU/sintoma.
        Usado ao abrir um novo serviço para mostrar o que funcionou/falhou.
        """
        query_parts = [queixa]
        if vehicle:
            query_parts += [vehicle.marca, vehicle.modelo, vehicle.motor]
        if ecu:
            query_parts += [ecu.fabricante, ecu.referencia]
        query = " ".join(p for p in query_parts if p)
        return self._store.search_similar(query, limit=limit)

    def similar_context(self, cases: list[ServiceCase]) -> str:
        """
        Gera texto de contexto com casos similares para o system prompt.
        Dados anonimizados (sem placa/VIN).
        """
        if not cases:
            return ""
        lines = ["=== Casos similares anteriores ==="]
        for c in cases:
            lines.append(c.summary(include_pii=False))
            if c.lessons:
                lines.append(f"  → Lições: {'; '.join(c.lessons)}")
            lines.append("")
        return "\n".join(lines)

    def add_action(self, case_id: str, description: str, result: str = "") -> Optional[ServiceCase]:
        case = self._store.get(case_id)
        if case:
            case.add_action(description, result)
            self._store.save(case)
        return case

    def add_dtc(self, case_id: str, dtc: str) -> Optional[ServiceCase]:
        case = self._store.get(case_id)
        if case and dtc not in case.dtcs:
            case.dtcs.append(dtc)
            self._store.save(case)
        return case

    def list_open(self) -> list[ServiceCase]:
        return self._store.list_open()

    def get(self, case_id: str) -> Optional[ServiceCase]:
        return self._store.get(case_id)
