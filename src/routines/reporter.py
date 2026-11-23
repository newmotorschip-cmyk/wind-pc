"""
AutoReporter — formata e entrega relatórios automáticos via NotificationManager.
Gera resumo matinal e retrospectiva semanal com entrega por todos os canais
disponíveis (Console, File, Telegram).
"""
from __future__ import annotations

from typing import Any

_MAX_CHARS = 4000  # margem abaixo do limite de 4096 chars do Telegram


class AutoReporter:
    """
    Ponte entre geradores de relatório (MorningSummary, RetrospectiveGenerator)
    e NotificationManager.
    Respeita o limite de caracteres do Telegram — trunca se necessário.
    """

    def __init__(self, orchestrator: Any, manager: Any) -> None:
        self._orc = orchestrator
        self._manager = manager

    # ── relatórios ────────────────────────────────────────────────────────────

    def send_morning_report(self) -> str:
        """Gera e entrega resumo matinal. Retorna texto gerado."""
        from src.routines.morning import MorningSummary
        text = MorningSummary(self._orc).generate()
        body = self._truncate(text)
        self._manager.info("Resumo Matinal WIND", body)
        return body

    def send_weekly_report(self) -> str:
        """Gera e entrega retrospectiva semanal. Retorna texto gerado."""
        from src.learning.retrospective import RetrospectiveGenerator
        retro = RetrospectiveGenerator(
            db_path="data/wind.db",
            autonomy_engine=getattr(self._orc, "decision_engine", None),
            note_manager=getattr(self._orc, "note_manager", None),
            curriculum=getattr(self._orc, "curriculum", None),
        )
        text = retro.generate()
        body = self._truncate(text)
        self._manager.info("Relatório Semanal WIND", body)
        return body

    def channels_active(self) -> list[str]:
        """Retorna nomes dos canais de notificação disponíveis."""
        return self._manager.available_channels()

    # ── utilitários ───────────────────────────────────────────────────────────

    @staticmethod
    def _truncate(text: str, limit: int = _MAX_CHARS) -> str:
        if len(text) <= limit:
            return text
        return text[:limit - 3] + "..."
