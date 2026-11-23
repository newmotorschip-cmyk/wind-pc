"""
Resumo matinal da WIND.
Consulta todos os subsistemas e gera um briefing em texto para o Felipe.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any


class MorningSummary:
    """
    Gera o resumo da manhã consultando casos, missões, propostas e notificações.
    Não faz I/O externo — apenas consulta os subsistemas já inicializados.
    """

    def __init__(self, orchestrator: Any) -> None:
        self._orc = orchestrator

    def generate(self) -> str:
        lines: list[str] = []
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        lines.append(f"=== Resumo WIND — {now} ===\n")

        lines.append(self._section_cases())
        lines.append(self._section_missions())
        lines.append(self._section_proposals())
        lines.append(self._section_notifications())
        lines.append(self._section_interfaces())

        return "\n".join(lines)

    # ── Seções ────────────────────────────────────────────────────────────────

    def _section_cases(self) -> str:
        try:
            cases = self._orc.cases.list_open()
            if not cases:
                return "• Casos: nenhum caso aberto.\n"
            lines = [f"• Casos em aberto ({len(cases)}):"]
            for c in cases[:5]:
                veh = f"{c.vehicle.marca} {c.vehicle.modelo}".strip() if hasattr(c, "vehicle") else ""
                lines.append(f"  - [{c.id[:8]}] {c.queixa}" + (f" ({veh})" if veh else ""))
            if len(cases) > 5:
                lines.append(f"  … e mais {len(cases) - 5} caso(s).")
            return "\n".join(lines) + "\n"
        except Exception as e:
            return f"• Casos: erro ao consultar — {e}\n"

    def _section_missions(self) -> str:
        try:
            missions = self._orc.missions._queue.list_active()
            if not missions:
                return "• Missões: nenhuma ativa.\n"
            lines = [f"• Missões ativas ({len(missions)}):"]
            for m in missions[:5]:
                prog = f" [{m.progress:.0%}]" if hasattr(m, "progress") and m.progress else ""
                lines.append(f"  - [{m.id[:8]}] {m.title} ({m.status.value}){prog}")
            if len(missions) > 5:
                lines.append(f"  … e mais {len(missions) - 5} missão(ões).")
            return "\n".join(lines) + "\n"
        except Exception as e:
            return f"• Missões: erro ao consultar — {e}\n"

    def _section_proposals(self) -> str:
        try:
            proposals = self._orc.calibration.list_pending()
            if not proposals:
                return "• Calibração: nenhuma proposta pendente.\n"
            lines = [f"• Propostas de calibração pendentes ({len(proposals)}):"]
            for p in proposals[:5]:
                flag = " ⚠️ LEGAL" if p.requires_legal_note else ""
                lines.append(f"  - [{p.id[:8]}] {p.ecu_family_id} — {p.vehicle_description}{flag}")
            return "\n".join(lines) + "\n"
        except Exception as e:
            return f"• Calibração: erro ao consultar — {e}\n"

    def _section_notifications(self) -> str:
        try:
            notifs = self._orc.notifications.read_recent(limit=5)
            if not notifs:
                return "• Notificações recentes: nenhuma.\n"
            lines = [f"• Notificações recentes ({len(notifs)}):"]
            for n in notifs:
                ts = datetime.fromtimestamp(n.created_at).strftime("%d/%m %H:%M") if n.created_at else ""
                lines.append(f"  - [{n.level.value.upper()}] {n.title}: {n.body[:60]}" + (f" ({ts})" if ts else ""))
            return "\n".join(lines) + "\n"
        except Exception as e:
            return f"• Notificações: erro ao consultar — {e}\n"

    def _section_interfaces(self) -> str:
        try:
            status = self._orc.flash_interfaces.status()
            parts = [f"{k}: {'OK' if v else 'indisponível'}" for k, v in status.items()]
            return f"• Interfaces hardware: {', '.join(parts) if parts else 'nenhuma'}\n"
        except Exception as e:
            return f"• Interfaces hardware: erro ao consultar — {e}\n"
