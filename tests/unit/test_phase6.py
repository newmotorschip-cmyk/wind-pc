"""
Testes da Fase 6 — iPhone, Voz e Experiência.
Cobre: notifications, routines, voice, api.
"""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Garantir que src/ está no sys.path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))


# ─── Notifications ────────────────────────────────────────────────────────────

class TestNotifLevel:
    def test_enum_values(self):
        from src.notifications.channel import NotifLevel
        assert NotifLevel.INFO.value    == "info"
        assert NotifLevel.WARNING.value == "warning"
        assert NotifLevel.ALERT.value   == "alert"


class TestNotification:
    def test_to_dict_round_trip(self):
        from src.notifications.channel import Notification, NotifLevel
        n = Notification(title="Teste", body="Corpo", level=NotifLevel.ALERT, source="unit")
        d = n.to_dict()
        assert d["title"] == "Teste"
        assert d["body"]  == "Corpo"
        assert d["level"] == "alert"
        assert d["source"] == "unit"

    def test_format_text_includes_title(self):
        from src.notifications.channel import Notification, NotifLevel
        n = Notification(title="Motor", body="Falha no sensor", level=NotifLevel.WARNING)
        text = n.format_text()
        assert "Motor" in text
        assert "Falha no sensor" in text


class TestConsoleChannel:
    def test_always_available(self):
        from src.notifications.channel import ConsoleChannel
        ch = ConsoleChannel()
        assert ch.is_available() is True
        assert ch.name() == "console"

    def test_send_returns_true(self, capsys):
        from src.notifications.channel import ConsoleChannel, Notification, NotifLevel
        ch = ConsoleChannel()
        n  = Notification(title="X", body="Y", level=NotifLevel.INFO)
        ok = ch.send(n)
        assert ok is True
        captured = capsys.readouterr()
        assert "X" in captured.out


class TestFileChannel:
    def test_send_and_read(self, tmp_path):
        from src.notifications.channel import FileChannel, Notification, NotifLevel
        p  = tmp_path / "notifs.jsonl"
        ch = FileChannel(p)
        n  = Notification(title="Título", body="Corpo", level=NotifLevel.INFO)
        ok = ch.send(n)
        assert ok is True
        recent = ch.read_recent(limit=5)
        assert len(recent) == 1
        assert recent[0].title == "Título"

    def test_read_recent_empty(self, tmp_path):
        from src.notifications.channel import FileChannel
        ch = FileChannel(tmp_path / "empty.jsonl")
        assert ch.read_recent() == []

    def test_always_available(self, tmp_path):
        from src.notifications.channel import FileChannel
        ch = FileChannel(tmp_path / "x.jsonl")
        assert ch.is_available() is True


class TestTelegramStub:
    def test_unavailable_without_env(self):
        from src.notifications.channel import TelegramStub
        with patch.dict(os.environ, {}, clear=True):
            # garante que as vars não estão definidas
            os.environ.pop("TELEGRAM_BOT_TOKEN",  None)
            os.environ.pop("TELEGRAM_CHAT_ID",    None)
            stub = TelegramStub()
            assert stub.is_available() is False
            assert stub.send(MagicMock()) is False


class TestNotificationManager:
    def test_notify_reaches_console(self, tmp_path, capsys):
        from src.notifications.manager import NotificationManager
        from src.notifications.channel import NotifLevel
        nm = NotificationManager(db_path=tmp_path / "wind.db")
        results = nm.notify("Alerta", "ECU não responde", NotifLevel.ALERT)
        assert results.get("console") is True

    def test_available_channels_includes_console(self, tmp_path):
        from src.notifications.manager import NotificationManager
        nm = NotificationManager(db_path=tmp_path / "wind.db")
        assert "console" in nm.available_channels()
        assert "file"    in nm.available_channels()

    def test_read_recent_empty(self, tmp_path):
        from src.notifications.manager import NotificationManager
        nm = NotificationManager(db_path=tmp_path / "wind.db")
        assert nm.read_recent() == []

    def test_convenience_methods(self, tmp_path, capsys):
        from src.notifications.manager import NotificationManager
        nm = NotificationManager(db_path=tmp_path / "wind.db")
        nm.alert("CRIT", "Falha crítica")
        nm.warning("WARN", "Aviso")
        nm.info("INFO", "Informação")
        notifs = nm.read_recent(limit=10)
        assert len(notifs) == 3


# ─── Voice ────────────────────────────────────────────────────────────────────

class TestConsoleTTS:
    def test_always_available(self):
        from src.voice.tts import ConsoleTTS
        tts = ConsoleTTS()
        assert tts.is_available() is True
        assert tts.name() == "console"

    def test_speak_returns_true(self, capsys):
        from src.voice.tts import ConsoleTTS
        tts = ConsoleTTS()
        ok  = tts.speak("Olá WIND")
        assert ok is True
        captured = capsys.readouterr()
        assert "Olá WIND" in captured.out


class TestWindowsSAPITTS:
    def test_unavailable_on_non_windows(self):
        from src.voice.tts import WindowsSAPITTS
        tts = WindowsSAPITTS()
        if sys.platform != "win32":
            assert tts.is_available() is False
            assert tts.speak("x") is False

    def test_speak_on_windows(self):
        from src.voice.tts import WindowsSAPITTS
        tts = WindowsSAPITTS()
        if sys.platform != "win32":
            pytest.skip("Teste somente no Windows")
        ok = tts.speak("Teste de voz WIND")
        assert isinstance(ok, bool)

    def test_single_quotes_escaped(self):
        """Aspas simples no texto não devem injetar código PowerShell."""
        from src.voice.tts import WindowsSAPITTS
        import subprocess
        tts = WindowsSAPITTS()
        if sys.platform != "win32":
            pytest.skip("Teste somente no Windows")
        # Texto com aspas simples — não deve lançar exceção
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            ok = tts.speak("O'Brien disse 'olá'")
        assert ok is True
        called_script = mock_run.call_args[0][0][-1]
        assert "''" in called_script  # aspas simples escapadas


class TestGetBestEngine:
    def test_returns_tts_engine(self):
        from src.voice.tts import get_best_engine, TTSEngine
        engine = get_best_engine()
        assert isinstance(engine, TTSEngine)
        assert engine.is_available() is True


class TestSTTStub:
    def test_not_available(self):
        from src.voice.stt import STTStub
        stt = STTStub()
        assert stt.is_available() is False
        assert stt.listen() is None
        assert "stub" in stt.status().lower()


# ─── Morning Summary ──────────────────────────────────────────────────────────

class TestMorningSummary:
    def _make_orc(self):
        orc = MagicMock()
        orc.cases.list_open.return_value = []
        orc.missions._queue.list_active.return_value = []
        orc.calibration.list_pending.return_value = []
        orc.notifications.read_recent.return_value = []
        orc.flash_interfaces.status.return_value = {"sm2": False, "bdm": False}
        return orc

    def test_generate_contains_header(self):
        from src.routines.morning import MorningSummary
        orc = self._make_orc()
        summary = MorningSummary(orc).generate()
        assert "Resumo WIND" in summary

    def test_generate_shows_no_cases(self):
        from src.routines.morning import MorningSummary
        orc = self._make_orc()
        summary = MorningSummary(orc).generate()
        assert "nenhum caso" in summary.lower()

    def test_generate_with_open_case(self):
        from src.routines.morning import MorningSummary
        orc = self._make_orc()
        case = MagicMock()
        case.id = "abc12345"
        case.queixa = "Mau funcionamento em partida a frio"
        case.vehicle = MagicMock()
        case.vehicle.marca = "VW"
        case.vehicle.modelo = "Golf"
        orc.cases.list_open.return_value = [case]
        summary = MorningSummary(orc).generate()
        assert "Golf" in summary or "abc123" in summary

    def test_subsystem_error_does_not_crash(self):
        from src.routines.morning import MorningSummary
        orc = self._make_orc()
        orc.cases.list_open.side_effect = RuntimeError("DB offline")
        summary = MorningSummary(orc).generate()
        assert "erro" in summary.lower()


# ─── API Server ───────────────────────────────────────────────────────────────

class TestWindAPIServer:
    """Testes de integração do servidor HTTP (stdlib only, porta efêmera)."""

    API_KEY = "test-key-wind-123"

    def _make_orc(self):
        orc = MagicMock()
        orc.status.return_value = {"ok": True}
        orc.process.return_value = "Resposta simulada da WIND."
        orc.cases.list_open.return_value = []
        orc.missions._queue.list_active.return_value = []
        orc.calibration.list_pending.return_value = []
        return orc

    def _get(self, port: int, path: str) -> tuple[int, dict]:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}",
            headers={"X-API-Key": self.API_KEY},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())

    def _post(self, port: int, path: str, body: dict) -> tuple[int, dict]:
        data = json.dumps(body).encode("utf-8")
        req  = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}",
            data=data,
            headers={"X-API-Key": self.API_KEY, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())

    def test_start_stop(self):
        from src.api.server import WindAPIServer
        orc = self._make_orc()
        srv = WindAPIServer(port=0, api_key=self.API_KEY, orchestrator=orc)
        port = srv.start()
        assert port > 0
        assert srv.is_running() is True
        srv.stop()
        assert srv.is_running() is False

    def test_status_endpoint(self):
        from src.api.server import WindAPIServer
        orc = self._make_orc()
        srv = WindAPIServer(port=0, api_key=self.API_KEY, orchestrator=orc)
        port = srv.start()
        try:
            status_code, body = self._get(port, "/status")
            assert status_code == 200
            assert body.get("ok") is True
        finally:
            srv.stop()

    def test_chat_endpoint(self):
        from src.api.server import WindAPIServer
        orc = self._make_orc()
        srv = WindAPIServer(port=0, api_key=self.API_KEY, orchestrator=orc)
        port = srv.start()
        try:
            status_code, body = self._post(port, "/chat", {"message": "Olá WIND"})
            assert status_code == 200
            assert "response" in body
        finally:
            srv.stop()

    def test_unauthorized_returns_401(self):
        from src.api.server import WindAPIServer
        import urllib.error
        orc = self._make_orc()
        srv = WindAPIServer(port=0, api_key=self.API_KEY, orchestrator=orc)
        port = srv.start()
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/status",
                headers={"X-API-Key": "wrong-key"},
            )
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(req, timeout=5)
            assert exc.value.code == 401
        finally:
            srv.stop()

    def test_not_found_returns_404(self):
        from src.api.server import WindAPIServer
        import urllib.error
        orc = self._make_orc()
        srv = WindAPIServer(port=0, api_key=self.API_KEY, orchestrator=orc)
        port = srv.start()
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/nao-existe",
                headers={"X-API-Key": self.API_KEY},
            )
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(req, timeout=5)
            assert exc.value.code == 404
        finally:
            srv.stop()

    def test_cases_endpoint(self):
        from src.api.server import WindAPIServer
        orc = self._make_orc()
        srv = WindAPIServer(port=0, api_key=self.API_KEY, orchestrator=orc)
        port = srv.start()
        try:
            status_code, body = self._get(port, "/cases")
            assert status_code == 200
            assert "total" in body
        finally:
            srv.stop()

    def test_notify_endpoint(self):
        from src.api.server import WindAPIServer
        orc = self._make_orc()
        srv = WindAPIServer(port=0, api_key=self.API_KEY, orchestrator=orc)
        port = srv.start()
        try:
            status_code, body = self._post(port, "/notify", {"text": "Aviso teste"})
            assert status_code == 200
            assert body.get("ok") is True
        finally:
            srv.stop()

    def test_chat_missing_message_returns_400(self):
        from src.api.server import WindAPIServer
        import urllib.error
        orc = self._make_orc()
        srv = WindAPIServer(port=0, api_key=self.API_KEY, orchestrator=orc)
        port = srv.start()
        try:
            with pytest.raises(urllib.error.HTTPError) as exc:
                self._post(port, "/chat", {})
            assert exc.value.code == 400
        finally:
            srv.stop()

    def test_server_url_property(self):
        from src.api.server import WindAPIServer
        orc = self._make_orc()
        srv = WindAPIServer(host="0.0.0.0", port=0, api_key=self.API_KEY, orchestrator=orc)
        port = srv.start()
        try:
            assert srv.url.startswith("http://")
            assert str(port) in srv.url
        finally:
            srv.stop()
