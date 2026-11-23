"""
Testes das correções da MISSÃO DEFINITIVA DE RECUPERAÇÃO.
P1a: continuidade de sessão (EpisodicMemory → system prompt)
P1b: STT real (STTServiceRecognizer / get_best_stt)
P2:  ClaudeCodeCLI subprocess wrapper
P4:  PWA funcional (arquivo HTML)
P6:  Ghidra validate_ghidra_install
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ── P1a: Continuidade de sessão ───────────────────────────────────────────────

class TestEpisodicContextLoader(unittest.TestCase):

    def _make_orchestrator_minimal(self, db_path):
        """Cria orchestrator com BD vazio."""
        from pathlib import Path
        from src.core.orchestrator import Orchestrator
        return Orchestrator(db_path=Path(db_path))

    def test_load_episodic_context_empty_db_returns_empty(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "wind.db")
            orc = self._make_orchestrator_minimal(db)
            ctx = orc._load_episodic_context()
            self.assertEqual(ctx, "")

    def test_load_episodic_context_with_data_returns_string(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "wind.db")
            orc = self._make_orchestrator_minimal(db)
            # Registra interação fake
            orc._episodic.record_interaction(
                user_text="Qual é o estado do projeto X?",
                wind_text="O projeto X está em andamento...",
                session_id="sess-test",
            )
            ctx = orc._load_episodic_context()
            self.assertIn("Felipe:", ctx)
            self.assertIn("WIND:", ctx)
            self.assertIn("Qual é o estado do projeto X?", ctx)

    def test_load_episodic_context_respects_limit(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "wind.db")
            orc = self._make_orchestrator_minimal(db)
            for i in range(10):
                orc._episodic.record_interaction(
                    user_text=f"mensagem {i}",
                    wind_text=f"resposta {i}",
                    session_id="sess-test",
                )
            ctx = orc._load_episodic_context(limit=3)
            # Deve conter no máximo 3 pares
            felipe_count = ctx.count("Felipe:")
            self.assertLessEqual(felipe_count, 3)

    def test_episodic_context_in_orchestrator_init(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "wind.db")
            from pathlib import Path
            from src.core.orchestrator import Orchestrator
            orc = Orchestrator(db_path=Path(db))
            # _episodic_context deve existir (string, pode ser vazia)
            self.assertIsInstance(orc._episodic_context, str)

    def test_episodic_context_header_format(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "wind.db")
            orc = self._make_orchestrator_minimal(db)
            orc._episodic.record_interaction(
                user_text="Olá WIND", wind_text="Olá Felipe!", session_id="s1"
            )
            ctx = orc._load_episodic_context()
            self.assertIn("[Histórico de sessões anteriores]", ctx)


# ── P1b: STT real ─────────────────────────────────────────────────────────────

class TestSTTServiceRecognizer(unittest.TestCase):

    def test_is_available_when_deps_installed(self):
        from src.voice.stt import STTServiceRecognizer
        stt = STTServiceRecognizer()
        # pyaudio e SpeechRecognition estão instalados neste ambiente
        self.assertTrue(stt.is_available())

    def test_name(self):
        from src.voice.stt import STTServiceRecognizer
        stt = STTServiceRecognizer()
        self.assertEqual(stt.name(), "speech_recognition_google")

    def test_status_not_stub(self):
        from src.voice.stt import STTServiceRecognizer
        stt = STTServiceRecognizer()
        self.assertNotIn("stub", stt.status().lower())

    def test_listen_returns_none_on_error(self):
        from src.voice.stt import STTServiceRecognizer
        stt = STTServiceRecognizer()
        # Sem microfone real em teste — deve retornar None, não levantar exceção
        result = stt.listen(timeout=0.1)
        self.assertIsNone(result)


class TestGetBestSTT(unittest.TestCase):

    def test_get_best_stt_returns_service_recognizer(self):
        from src.voice.stt import get_best_stt, STTServiceRecognizer
        stt = get_best_stt()
        # pyaudio e SR instalados → deve retornar STTServiceRecognizer
        self.assertIsInstance(stt, STTServiceRecognizer)

    def test_get_best_stt_is_available(self):
        from src.voice.stt import get_best_stt
        self.assertTrue(get_best_stt().is_available())

    def test_get_best_stt_fallback_when_unavailable(self):
        from src.voice.stt import get_best_stt, STTStub
        # Simula ausência de dependências
        with patch("src.voice.stt.STTServiceRecognizer.is_available", return_value=False):
            stt = get_best_stt()
        self.assertIsInstance(stt, STTStub)

    def test_orchestrator_uses_service_recognizer(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "wind.db")
            from pathlib import Path
            from src.core.orchestrator import Orchestrator
            from src.voice.stt import STTServiceRecognizer
            orc = Orchestrator(db_path=Path(db))
            self.assertIsInstance(orc._stt, STTServiceRecognizer)

    def test_orchestrator_status_includes_stt(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "wind.db")
            from pathlib import Path
            from src.core.orchestrator import Orchestrator
            orc = Orchestrator(db_path=Path(db))
            st = orc.status()
            self.assertIn("stt", st)
            self.assertIn("stt_available", st)
            self.assertTrue(st["stt_available"])


# ── P2: Claude Code CLI wrapper ───────────────────────────────────────────────

class TestClaudeCodeCLI(unittest.TestCase):

    def test_find_binary_returns_none_when_not_installed(self):
        from src.adapters.claude_code import _find_claude_binary
        with patch("shutil.which", return_value=None):
            result = _find_claude_binary()
        # Pode ser None ou um path que não existe
        if result is not None:
            from pathlib import Path
            self.assertFalse(Path(result).exists())

    def test_is_available_false_without_cli(self):
        from src.adapters.claude_code import ClaudeCodeCLI
        with patch("src.adapters.claude_code._find_claude_binary", return_value=None):
            cli = ClaudeCodeCLI()
        self.assertFalse(cli.is_available())

    def test_name(self):
        from src.adapters.claude_code import ClaudeCodeCLI
        self.assertEqual(ClaudeCodeCLI().name(), "claude_code_cli")

    def test_install_hint_contains_npm(self):
        from src.adapters.claude_code import ClaudeCodeCLI
        hint = ClaudeCodeCLI.install_hint()
        self.assertIn("npm", hint.lower())

    def test_run_raises_when_unavailable(self):
        from src.adapters.claude_code import ClaudeCodeCLI
        with patch("src.adapters.claude_code._find_claude_binary", return_value=None):
            cli = ClaudeCodeCLI()
        with self.assertRaises(RuntimeError):
            cli.run("hello")

    def test_run_calls_subprocess_when_available(self):
        from src.adapters.claude_code import ClaudeCodeCLI
        fake_binary = "/fake/claude"
        with patch("src.adapters.claude_code._find_claude_binary", return_value=fake_binary):
            cli = ClaudeCodeCLI()
        self.assertTrue(cli.is_available())
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="resultado", stderr="")
            result = cli.run("gere um hello world")
        mock_run.assert_called_once()
        self.assertEqual(result, "resultado")

    def test_run_raises_on_nonzero_exit(self):
        from src.adapters.claude_code import ClaudeCodeCLI
        fake_binary = "/fake/claude"
        with patch("src.adapters.claude_code._find_claude_binary", return_value=fake_binary):
            cli = ClaudeCodeCLI()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="erro")
            with self.assertRaises(RuntimeError):
                cli.run("prompt")


class TestGetClaudeCode(unittest.TestCase):

    def test_returns_api_adapter_when_cli_unavailable(self):
        from src.adapters.claude_code import get_claude_code, ClaudeCodeAdapter
        with patch("src.adapters.claude_code._find_claude_binary", return_value=None):
            adapter = get_claude_code()
        self.assertIsInstance(adapter, ClaudeCodeAdapter)

    def test_returns_cli_when_available(self):
        from src.adapters.claude_code import get_claude_code, ClaudeCodeCLI
        with patch("src.adapters.claude_code._find_claude_binary", return_value="/fake/claude"):
            adapter = get_claude_code()
        self.assertIsInstance(adapter, ClaudeCodeCLI)


# ── P4: PWA ────────────────────────────────────────────────────────────────────

class TestPWA(unittest.TestCase):

    def _load_html(self):
        from pathlib import Path
        p = Path(__file__).parent.parent.parent / "web" / "wind_voice" / "index.html"
        return p.read_text(encoding="utf-8")

    def test_pwa_has_text_input(self):
        html = self._load_html()
        self.assertIn('id="txtInput"', html)

    def test_pwa_has_send_button(self):
        html = self._load_html()
        self.assertIn('id="sendBtn"', html)

    def test_pwa_has_mic_button(self):
        html = self._load_html()
        self.assertIn('id="micBtn"', html)

    def test_pwa_has_project_panel(self):
        html = self._load_html()
        self.assertIn('id="panel-proj"', html)

    def test_pwa_has_status_panel(self):
        html = self._load_html()
        self.assertIn('id="panel-status"', html)

    def test_pwa_has_chat_panel(self):
        html = self._load_html()
        self.assertIn('id="panel-chat"', html)

    def test_pwa_has_tabs(self):
        html = self._load_html()
        self.assertIn("switchTab", html)

    def test_pwa_has_wol_function(self):
        html = self._load_html()
        self.assertIn("sendWoL", html)

    def test_pwa_calls_chat_api(self):
        html = self._load_html()
        self.assertIn("/chat", html)

    def test_pwa_has_settings_persistence(self):
        html = self._load_html()
        self.assertIn("localStorage", html)


# ── P6: Ghidra validate_ghidra_install ───────────────────────────────────────

class TestGhidraValidation(unittest.TestCase):

    def test_validate_missing_root(self):
        from src.rev_eng.ghidra_client import validate_ghidra_install
        from pathlib import Path
        result = validate_ghidra_install(Path("/nao/existe/ghidra"))
        self.assertFalse(result["ok"])
        self.assertFalse(result["root_exists"])
        self.assertIn("não encontrado", result["message"].lower())

    def test_validate_returns_dict_with_required_keys(self):
        from src.rev_eng.ghidra_client import validate_ghidra_install
        from pathlib import Path
        result = validate_ghidra_install(Path("/nao/existe"))
        for key in ("ok", "root_exists", "headless", "processors_ok", "message", "install_hint"):
            self.assertIn(key, result)

    def test_validate_install_hint_mentions_ghidra_sre(self):
        from src.rev_eng.ghidra_client import validate_ghidra_install
        from pathlib import Path
        result = validate_ghidra_install(Path("/nao/existe"))
        self.assertIn("ghidra-sre.org", result["install_hint"])

    def test_validate_real_ghidra_path_reports_no_headless(self):
        """O caminho configurado existe mas não tem analyzeHeadless (build dev)."""
        from src.rev_eng.ghidra_client import validate_ghidra_install, GHIDRA_PATH
        result = validate_ghidra_install(GHIDRA_PATH)
        self.assertTrue(result["root_exists"])
        # analyzeHeadless NÃO existe nesta instalação de desenvolvimento
        self.assertFalse(result["ok"])
        self.assertIsNone(result["headless"])

    def test_validate_with_fake_headless(self):
        """Simula instalação com analyzeHeadless presente."""
        from src.rev_eng.ghidra_client import validate_ghidra_install
        from pathlib import Path
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            # Cria estrutura mínima de release
            root = Path(tmp) / "ghidra_fake"
            support = root / "support"
            support.mkdir(parents=True)
            headless = support / "analyzeHeadless.bat"
            headless.write_text("@echo off\n")
            result = validate_ghidra_install(root)
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["headless"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
