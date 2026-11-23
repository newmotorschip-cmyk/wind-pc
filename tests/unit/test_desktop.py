"""Testes do Desktop Agent e Wake-on-LAN (Fase 10)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from unittest.mock import patch, MagicMock
from src.desktop.agent import DesktopAgent
from src.desktop.wol import _parse_mac, magic_packet_bytes


# ── DesktopAgent ────────────────────────────────────────────────────────────

class TestDesktopAgent(unittest.TestCase):

    def setUp(self):
        self.agent = DesktopAgent()

    def test_allowed_apps_list(self):
        apps = self.agent.allowed_apps()
        assert "claude" in apps
        assert "codex"  in apps
        assert "terminal" in apps

    def test_unknown_command_returns_error(self):
        result = self.agent.execute("explodir_tudo")
        assert result["ok"] is False
        assert "não reconhecido" in result["error"]

    def test_open_app_unknown_returns_error(self):
        result = self.agent.execute("open_app", app="photoshop")
        assert result["ok"] is False
        assert "não permitido" in result["error"]

    @patch("src.desktop.agent.subprocess.Popen")
    def test_open_app_claude(self, mock_popen):
        mock_popen.return_value = MagicMock()
        result = self.agent.execute("open_app", app="claude")
        assert result["ok"] is True
        assert mock_popen.called

    @patch("src.desktop.agent.subprocess.Popen")
    def test_open_app_codex(self, mock_popen):
        mock_popen.return_value = MagicMock()
        result = self.agent.execute("open_app", app="codex")
        assert result["ok"] is True

    @patch("src.desktop.agent.subprocess.Popen")
    def test_search_web_builds_url(self, mock_popen):
        mock_popen.return_value = MagicMock()
        result = self.agent.execute("search_web", query="Bosch EDC17")
        assert result["ok"] is True
        # verifica que a chamada aconteceu com URL do Google
        args = mock_popen.call_args[0][0]
        assert any("google.com/search" in str(a) and "Bosch" in str(a) for a in args)

    def test_search_web_empty_query(self):
        result = self.agent.execute("search_web", query="")
        assert result["ok"] is False

    def test_search_web_whitespace_query(self):
        result = self.agent.execute("search_web", query="   ")
        assert result["ok"] is False

    @patch("src.desktop.agent.subprocess.Popen")
    def test_open_url_https(self, mock_popen):
        mock_popen.return_value = MagicMock()
        result = self.agent.execute("open_url", url="https://example.com")
        assert result["ok"] is True

    def test_open_url_rejects_ftp(self):
        result = self.agent.execute("open_url", url="ftp://example.com/file")
        assert result["ok"] is False
        assert "http" in result["error"]

    def test_open_url_rejects_empty(self):
        result = self.agent.execute("open_url", url="")
        assert result["ok"] is False

    def test_open_url_rejects_javascript(self):
        result = self.agent.execute("open_url", url="javascript:alert(1)")
        assert result["ok"] is False

    def test_get_status_returns_ok(self):
        result = self.agent.execute("get_status")
        assert result["ok"] is True
        assert "status" in result
        assert "online" in result["status"]
        assert result["status"]["online"] is True

    def test_get_status_has_pc_name(self):
        result = self.agent.execute("get_status")
        assert "pc" in result["status"]
        assert len(result["status"]["pc"]) > 0


# ── Wake-on-LAN ─────────────────────────────────────────────────────────────

class TestWakeOnLAN(unittest.TestCase):

    def test_parse_mac_colon(self):
        b = _parse_mac("AA:BB:CC:DD:EE:FF")
        assert b == bytes.fromhex("AABBCCDDEEFF")

    def test_parse_mac_dash(self):
        b = _parse_mac("AA-BB-CC-DD-EE-FF")
        assert b == bytes.fromhex("AABBCCDDEEFF")

    def test_parse_mac_lowercase(self):
        b = _parse_mac("aa:bb:cc:dd:ee:ff")
        assert b == bytes.fromhex("aabbccddeeff")

    def test_parse_mac_invalid_raises(self):
        with self.assertRaises(ValueError):
            _parse_mac("ZZ:BB:CC:DD:EE:FF")

    def test_parse_mac_too_short_raises(self):
        with self.assertRaises(ValueError):
            _parse_mac("AA:BB:CC")

    def test_magic_packet_length(self):
        pkt = magic_packet_bytes("AA:BB:CC:DD:EE:FF")
        assert len(pkt) == 102  # 6 + 16*6

    def test_magic_packet_starts_with_ff(self):
        pkt = magic_packet_bytes("AA:BB:CC:DD:EE:FF")
        assert pkt[:6] == b"\xff\xff\xff\xff\xff\xff"

    def test_magic_packet_repeats_mac_16_times(self):
        mac = "11:22:33:44:55:66"
        pkt = magic_packet_bytes(mac)
        mac_bytes = bytes.fromhex("112233445566")
        # Os 6 bytes do header + 16 repetições do MAC
        assert pkt[6:12]       == mac_bytes  # 1ª repetição
        assert pkt[96:102]     == mac_bytes  # 16ª repetição (6 + 15*6 = 96)
        assert pkt.count(mac_bytes) == 16


if __name__ == "__main__":
    unittest.main(verbosity=2)
