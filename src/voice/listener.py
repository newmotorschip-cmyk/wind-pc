"""
Listener de voz — escuta contínua com detecção de wake word.
Requer: pip install SpeechRecognition pyaudio
Fallback offline: pip install vosk (modelo pt-BR em data/vosk-model-pt/)
"""
from __future__ import annotations

import threading
import queue
import logging
from typing import Callable

logger = logging.getLogger(__name__)

WAKE_WORDS = {"wind", "hey wind", "ei wind", "vento", "hey vento"}
DEFAULT_TIMEOUT = 8   # segundos ouvindo após wake word
DEFAULT_PAUSE   = 1.0 # pausa de silêncio que encerra a fala


def _sr_available() -> bool:
    try:
        import speech_recognition  # noqa
        import pyaudio  # noqa
        return True
    except ImportError:
        return False


class VoiceListener:
    """
    Escuta contínua com wake word.
    Quando detecta a palavra-chave, captura o comando e chama on_command(text).
    """

    def __init__(
        self,
        on_command: Callable[[str], None],
        wake_words: set[str] | None = None,
        language: str = "pt-BR",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._on_command = on_command
        self._wake_words = wake_words or WAKE_WORDS
        self._language   = language
        self._timeout    = timeout
        self._running    = False
        self._thread: threading.Thread | None = None
        self._cmd_queue: queue.Queue[str] = queue.Queue()
        self.available   = _sr_available()

    def start(self) -> bool:
        """Inicia escuta em background. Retorna False se dependências ausentes."""
        if not self.available:
            logger.warning("VoiceListener: speech_recognition/pyaudio não instalados.")
            return False
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("VoiceListener: escuta iniciada (wake words: %s)", self._wake_words)
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _listen_loop(self) -> None:
        import speech_recognition as sr  # type: ignore

        recognizer = sr.Recognizer()
        recognizer.pause_threshold = DEFAULT_PAUSE
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True

        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("VoiceListener: microfone pronto. Diga '%s' para ativar.", list(self._wake_words)[0])

            while self._running:
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    text  = recognizer.recognize_google(audio, language=self._language).lower().strip()
                    logger.debug("Ouvido: %s", text)

                    # Verificar wake word
                    triggered = any(ww in text for ww in self._wake_words)
                    if triggered:
                        # Remover wake word do texto, pegar o restante como comando
                        cmd = text
                        for ww in self._wake_words:
                            cmd = cmd.replace(ww, "").strip(" ,.")
                        if cmd:
                            self._on_command(cmd)
                        else:
                            # Wake word sem comando → ouvir próxima frase
                            try:
                                audio2 = recognizer.listen(source, timeout=self._timeout, phrase_time_limit=15)
                                cmd2   = recognizer.recognize_google(audio2, language=self._language).strip()
                                if cmd2:
                                    self._on_command(cmd2)
                            except (sr.WaitTimeoutError, sr.UnknownValueError):
                                pass

                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as exc:
                    logger.warning("VoiceListener: erro de reconhecimento: %s", exc)
                except Exception as exc:
                    logger.error("VoiceListener: erro inesperado: %s", exc)
                    if not self._running:
                        break

    @staticmethod
    def install_hint() -> str:
        return (
            "Para ativar voz nativa:\n"
            "  pip install SpeechRecognition\n"
            "  pip install pyaudio\n"
            "  (Windows: se pyaudio falhar, use: pip install pipwin; pipwin install pyaudio)\n"
        )
