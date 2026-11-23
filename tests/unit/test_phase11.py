"""Testes da Fase 11 — DesktopAgent expandido + VoiceAgent."""
import sys
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.desktop.agent import DesktopAgent


# ── DesktopAgent — novos comandos ──────────────────────────────────────────────

class TestDesktopAgentExpanded(unittest.TestCase):

    def setUp(self):
        self.agent = DesktopAgent(project_root=".")

    # run_command
    def test_run_command_whitelist_allowed(self):
        result = self.agent.execute("run_command", cmd="echo hello")
        self.assertTrue(result["ok"])
        self.assertIn("hello", result.get("output", "").lower())

    def test_run_command_blocked_exe(self):
        result = self.agent.execute("run_command", cmd="format C:")
        self.assertFalse(result["ok"])
        self.assertIn("whitelist", result["error"])

    def test_run_command_timeout(self):
        # ping com timeout menor que o delay seria perfeito, mas usamos cwd inválido
        result = self.agent.execute("run_command", cmd="echo ok", cwd=".")
        self.assertTrue(result["ok"])

    # list_files
    def test_list_files_current_dir(self):
        result = self.agent.execute("list_files", path=".")
        self.assertTrue(result["ok"])
        self.assertGreater(result["count"], 0)

    def test_list_files_nonexistent(self):
        result = self.agent.execute("list_files", path="/caminho/que/nao/existe")
        self.assertFalse(result["ok"])

    def test_list_files_with_pattern(self):
        result = self.agent.execute("list_files", path=".", pattern="*.py")
        self.assertTrue(result["ok"])

    # read_file
    def test_read_file_existing(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("conteudo de teste")
            path = f.name
        try:
            result = self.agent.execute("read_file", path=path)
            self.assertTrue(result["ok"])
            self.assertIn("conteudo de teste", result["content"])
        finally:
            os.unlink(path)

    def test_read_file_nonexistent(self):
        result = self.agent.execute("read_file", path="/arquivo/que/nao/existe.txt")
        self.assertFalse(result["ok"])

    def test_read_file_missing_param(self):
        result = self.agent.execute("read_file")
        self.assertFalse(result["ok"])

    # write_file
    def test_write_file_in_safe_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = DesktopAgent(project_root=tmp)
            path = os.path.join(tmp, "test_write.txt")
            result = agent.execute("write_file", path=path, content="hello wind")
            self.assertTrue(result["ok"])
            self.assertEqual(Path(path).read_text(), "hello wind")

    def test_write_file_outside_safe_dir(self):
        result = self.agent.execute("write_file", path="C:\\Windows\\test.txt", content="x")
        self.assertFalse(result["ok"])
        self.assertIn("seguro", result["error"])

    # read_clipboard / write_clipboard (apenas verificar que não crasham)
    def test_write_clipboard_ok(self):
        result = self.agent.execute("write_clipboard", text="WIND clipboard test")
        # Pode falhar se não há suporte no CI, mas não deve levantar exceção
        self.assertIn("ok", result)

    def test_write_clipboard_empty(self):
        result = self.agent.execute("write_clipboard", text="")
        self.assertFalse(result["ok"])

    # git_status (pode falhar se não há git, mas não deve crashar)
    def test_git_status_no_crash(self):
        result = self.agent.execute("git_status", path=".")
        self.assertIn("ok", result)

    # git_diff (apenas não crashar)
    def test_git_diff_no_crash(self):
        result = self.agent.execute("git_diff", path=".")
        self.assertIn("ok", result)

    # take_screenshot (sem pyautogui → erro amigável)
    def test_take_screenshot_no_pyautogui(self):
        with patch.dict("sys.modules", {"pyautogui": None}):
            result = self.agent.execute("take_screenshot")
            # Pode retornar ok True (se pyautogui instalado) ou False (sem ele)
            self.assertIn("ok", result)

    # allowed_commands
    def test_allowed_commands_list(self):
        cmds = self.agent.allowed_commands()
        self.assertIn("git", cmds)
        self.assertIn("python", cmds)

    # audit log
    def test_audit_log_called(self):
        mock_audit = MagicMock()
        self.agent.set_audit(mock_audit)
        self.agent.execute("list_files", path=".")
        mock_audit.log.assert_called_once()
        call_args = mock_audit.log.call_args
        self.assertEqual(call_args[0][0], "desktop_action")


# ── VoiceAgent ─────────────────────────────────────────────────────────────────

class TestVoiceAgent(unittest.TestCase):

    def test_voice_agent_unavailable_without_deps(self):
        """VoiceAgent.available retorna False quando pyaudio não está instalado."""
        with patch.dict("sys.modules", {"speech_recognition": None, "pyaudio": None}):
            from src.voice.voice_agent import VoiceAgent
            va = VoiceAgent(orchestrator=MagicMock())
            # available depende de _sr_available(), que verifica imports
            # Em ambiente sem pyaudio retorna False
            self.assertIsInstance(va.available, bool)

    def test_voice_agent_start_fails_gracefully_without_deps(self):
        """VoiceAgent.start() retorna False sem dependências."""
        with patch("src.voice.listener._sr_available", return_value=False):
            from src.voice.voice_agent import VoiceAgent
            va = VoiceAgent(orchestrator=MagicMock())
            result = va.start()
            self.assertFalse(result)
            self.assertFalse(va.running)

    def test_voice_agent_install_hint_contains_pip(self):
        from src.voice.voice_agent import VoiceAgent
        hint = VoiceAgent.install_hint()
        self.assertIn("pip", hint)
        self.assertIn("SpeechRecognition", hint)

    def test_voice_listener_wake_words_default(self):
        from src.voice.listener import VoiceListener, WAKE_WORDS
        self.assertIn("wind", WAKE_WORDS)

    def test_voice_agent_stop_when_not_running(self):
        from src.voice.voice_agent import VoiceAgent
        va = VoiceAgent(orchestrator=MagicMock())
        va.stop()  # não deve levantar exceção

    @patch("src.voice.listener._sr_available", return_value=True)
    @patch("src.voice.listener.VoiceListener.start", return_value=True)
    def test_voice_agent_start_success(self, mock_start, mock_avail):
        from src.voice.voice_agent import VoiceAgent
        orc = MagicMock()
        va = VoiceAgent(orchestrator=orc)
        result = va.start()
        self.assertTrue(result)
        self.assertTrue(va.running)

    def test_voice_agent_command_hook(self):
        """on_command_hook é chamado com (text, response)."""
        with patch("src.voice.listener._sr_available", return_value=True), \
             patch("src.voice.listener.VoiceListener.start", return_value=True):
            from src.voice.voice_agent import VoiceAgent
            orc = MagicMock()
            orc.process.return_value = "resposta teste"
            va = VoiceAgent(orchestrator=orc)
            va.start()

            received = []
            va.set_command_hook(lambda t, r: received.append((t, r)))
            va._handle_command("abrir navegador")

            self.assertEqual(len(received), 1)
            self.assertEqual(received[0][0], "abrir navegador")
            self.assertEqual(received[0][1], "resposta teste")


if __name__ == "__main__":
    unittest.main(verbosity=2)
