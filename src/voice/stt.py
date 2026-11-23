"""
Stub de STT (Speech-to-Text) da WIND.
Fase 6: reconhece que captura de áudio requer integração futura
(Windows Speech Recognition API ou Whisper local).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class STTEngine(ABC):
    @abstractmethod
    def listen(self, timeout: float = 5.0) -> str | None: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def name(self) -> str: ...


class STTStub(STTEngine):
    """
    Stub: STT não implementado na Fase 6.
    Integração futura: Windows Speech Recognition ou whisper.cpp local.
    """

    def name(self) -> str:
        return "stub"

    def is_available(self) -> bool:
        return False

    def listen(self, timeout: float = 5.0) -> str | None:
        return None

    def status(self) -> str:
        return (
            "STT não implementado (Fase 6 stub). "
            "Integração futura: Windows Speech Recognition ou whisper.cpp."
        )
