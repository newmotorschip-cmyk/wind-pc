"""
Motor TTS da WIND.
ConsoleTTS: sempre disponível (imprime o texto).
WindowsSAPITTS: usa PowerShell + Windows SAPI — sem dependências extras.
"""
from __future__ import annotations

import subprocess
import sys
from abc import ABC, abstractmethod


class TTSEngine(ABC):
    @abstractmethod
    def speak(self, text: str) -> bool: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def name(self) -> str: ...


class ConsoleTTS(TTSEngine):
    """Fallback universal: imprime o texto no terminal."""

    def name(self) -> str:
        return "console"

    def is_available(self) -> bool:
        return True

    def speak(self, text: str) -> bool:
        print(f"[TTS] {text}")
        return True


class WindowsSAPITTS(TTSEngine):
    """
    Síntese de voz usando Windows SAPI via PowerShell.
    Não requer pyttsx3 nem qualquer lib Python de áudio.
    """

    def name(self) -> str:
        return "windows_sapi"

    def is_available(self) -> bool:
        return sys.platform == "win32"

    def speak(self, text: str) -> bool:
        if not self.is_available():
            return False
        # Escapa aspas simples para evitar injeção no script PowerShell
        safe_text = text.replace("'", "''")
        ps_script = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}')"
        try:
            result = subprocess.run(
                ["powershell", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                timeout=30,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False


def get_best_engine() -> TTSEngine:
    """Retorna o melhor motor disponível."""
    engines: list[TTSEngine] = [WindowsSAPITTS(), ConsoleTTS()]
    for engine in engines:
        if engine.is_available():
            return engine
    return ConsoleTTS()  # sempre disponível
