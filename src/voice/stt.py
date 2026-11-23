"""
STT (Speech-to-Text) da WIND.
Usa SpeechRecognition + PyAudio quando disponíveis; fallback para stub.
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
    """Stub: pyaudio/SpeechRecognition não disponíveis."""

    def name(self) -> str:
        return "stub"

    def is_available(self) -> bool:
        return False

    def listen(self, timeout: float = 5.0) -> str | None:
        return None

    def status(self) -> str:
        return "STT stub: pyaudio/SpeechRecognition não instalados."


class STTServiceRecognizer(STTEngine):
    """Captura de áudio via SpeechRecognition + Google Speech API (pt-BR)."""

    def name(self) -> str:
        return "speech_recognition_google"

    def is_available(self) -> bool:
        try:
            import speech_recognition  # noqa: F401
            import pyaudio              # noqa: F401
            return True
        except ImportError:
            return False

    def listen(self, timeout: float = 5.0) -> str | None:
        if not self.is_available():
            return None
        try:
            import speech_recognition as sr  # type: ignore
            recognizer = sr.Recognizer()
            recognizer.dynamic_energy_threshold = True
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
            return recognizer.recognize_google(audio, language="pt-BR")
        except Exception:
            return None

    def status(self) -> str:
        return "STT ativo (SpeechRecognition + Google pt-BR)."


def get_best_stt() -> STTEngine:
    """Retorna o melhor STT disponível neste ambiente."""
    engine = STTServiceRecognizer()
    return engine if engine.is_available() else STTStub()
