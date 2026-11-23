"""Módulo de voz nativo — STT + wake word + TTS para o PC."""
from .listener import VoiceListener
from .voice_agent import VoiceAgent

__all__ = ["VoiceListener", "VoiceAgent"]
