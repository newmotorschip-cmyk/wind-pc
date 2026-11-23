"""
Retrospectiva semanal da WIND — Fase 8.
Gera um resumo de evolução: o que foi aprendido, decidido e calibrado na semana.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Optional


def _fmt_dt(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m %H:%M") if ts else "—"


class RetrospectiveGenerator:
    """
    Consulta audit log, decisões e notas para gerar retrospectiva semanal.
    Usa apenas o que está disponível — subsistema ausente não impede a geração.
    """
    def __init__(
        self,
        db_path: str | Path = "data/wind.db",
        autonomy_engine=None,
        note_manager=None,
        curriculum=None,
    ) -> None:
        self._db_path    = Path(db_path)
        self._engine     = autonomy_engine
        self._notes      = note_manager
        self._curriculum = curriculum

    def generate(self, days: int = 7) -> str:
        since = time.time() - (days * 86400)
        sections: list[str] = []

        sections.append(f"=== Retrospectiva WIND — últimos {days} dias ===")
        sections.append(f"Gerada em {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")

        # Nível de autonomia
        if self._engine:
            try:
                profile = self._engine.profile
                level   = profile.current_level
                sections.append(f"Nível de autonomia: {level.label()}")
                history = profile.history[-3:] if profile.history else []
                if history:
                    sections.append("Últimas alterações de nível:")
                    for h in history:
                        ts  = _fmt_dt(float(h.get("timestamp", 0)))
                        frm = h.get("from_level", "?")
                        to  = h.get("to_level", "?")
                        why = h.get("reason", "")[:60]
                        sections.append(f"  {ts} {frm}→{to}: {why}")
            except Exception:
                sections.append("Nível de autonomia: (erro ao consultar)")

        # Decisões da semana
        if self._engine:
            try:
                stats = self._engine._store.stats(since=since)
                total = stats.get("total", 0)
                auto  = stats.get("autonomous", 0)
                by_st = stats.get("by_status", {})
                sections.append(f"\nDecisões na semana: {total} total | {auto} autônomas")
                if by_st:
                    for status, count in by_st.items():
                        sections.append(f"  {status}: {count}")
            except Exception:
                sections.append("\nDecisões: (erro ao consultar)")

        # Notas de aprendizado
        if self._notes:
            try:
                note_stats = self._notes.stats()
                proposed  = note_stats.get("proposed", 0)
                validated = note_stats.get("validated", 0)
                obsolete  = note_stats.get("obsolete", 0)
                sections.append(
                    f"\nNotas de aprendizado: {validated} validadas | "
                    f"{proposed} propostas | {obsolete} obsoletas"
                )
                # Notas validadas recentemente
                recent_validated = self._notes.list_validated(limit=5)
                if recent_validated:
                    sections.append("Validadas recentemente:")
                    for n in recent_validated[:3]:
                        ts = _fmt_dt(n.validated_at)
                        sections.append(f"  [{ts}] {n.topic[:55]} ({n.confidence:.0%})")
                # Notas propostas aguardando validação
                pending_notes = self._notes.list_proposed(limit=5)
                if pending_notes:
                    sections.append(f"Aguardando validação ({len(pending_notes)}):")
                    for n in pending_notes[:3]:
                        sections.append(f"  {n.summary_line()}")
            except Exception:
                sections.append("\nNotas: (erro ao consultar)")

        # Currículo
        if self._curriculum:
            try:
                sections.append("\n" + self._curriculum.summary())
            except Exception:
                sections.append("\nCurrículo: (erro ao consultar)")

        # Auditoria SQLite — erros e eventos registrados
        try:
            sections.append(self._audit_summary(since))
        except Exception:
            pass

        sections.append("\n=== fim da retrospectiva ===")
        return "\n".join(sections)

    def _audit_summary(self, since: float) -> str:
        """Resumo do audit log SQLite (tabela audit_log se existir)."""
        if not self._db_path.exists():
            return ""
        try:
            import sqlite3
            with sqlite3.connect(str(self._db_path)) as conn:
                # Verifica se a tabela existe
                exists = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='audit_log'"
                ).fetchone()
                if not exists:
                    return ""
                rows = conn.execute(
                    "SELECT action, COUNT(*) FROM audit_log WHERE timestamp>=? GROUP BY action",
                    (since,)
                ).fetchall()
            if not rows:
                return ""
            lines = ["\nAuditoria (semana):"]
            for action, count in rows:
                lines.append(f"  {action}: {count}x")
            return "\n".join(lines)
        except Exception:
            return ""
