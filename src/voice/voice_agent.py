"""
VoiceAgent — integra VoiceListener com o Orchestrator.
Ouve wake word "WIND", processa via LLM, fala a resposta.
"""
from __future__ import annotations

import logging
from typing import Any

from .listener import VoiceListener

logger = logging.getLogger(__name__)


class VoiceAgent:
    """Coordena voz → Orchestrator → TTS."""

    def __init__(self, orchestrator: Any, tts: Any | None = None) -> None:
        self._orc = orchestrator
        self._tts = tts or getattr(orchestrator, "tts", None)
        self._listener: VoiceListener | None = None
        self.running = False
        self._on_command_hook: Any = None

    def set_command_hook(self, hook: Any) -> None:
        """Hook chamado com (text, response) após cada comando processado."""
        self._on_command_hook = hook

    def start(self) -> bool:
        """Inicia o agente de voz. Retorna False se dependências ausentes."""
        self._listener = VoiceListener(on_command=self._handle_command)
        ok = self._listener.start()
        if ok:
            self.running = True
            logger.info("VoiceAgent: ativo. Diga 'WIND' para ativar.")
        return ok

    def stop(self) -> None:
        self.running = False
        if self._listener:
            self._listener.stop()

    def _handle_command(self, text: str) -> None:
        """Chamado pelo listener com o texto do comando."""
        logger.info("Comando de voz: %s", text)
        try:
            # Feedback auditivo imediato
            if self._tts:
                self._tts.speak("Processando...")

            response = self._orc.process(text)

            # Falar resposta (limitar a 300 chars para TTS ficar razoável)
            tts_text = response[:300] if response else "Sem resposta."
            if self._tts:
                self._tts.speak(tts_text)

            if self._on_command_hook:
                self._on_command_hook(text, response)

        except Exception as exc:
            logger.error("VoiceAgent: erro ao processar comando: %s", exc)
            if self._tts:
                self._tts.speak("Erro ao processar.")

    @property
    def available(self) -> bool:
        if self._listener is None:
            from .listener import _sr_available
            return _sr_available()
        return self._listener.available

    @staticmethod
    def install_hint() -> str:
        return VoiceListener.install_hint()
