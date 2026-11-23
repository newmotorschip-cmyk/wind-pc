"""Testes da Fase 13 — TelegramChannel + ProactiveDelivery."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ── TelegramChannel alias ─────────────────────────────────────────────────────

class TestTelegramChannelAlias(unittest.TestCase):

    def test_telegram_channel_is_exported(self):
        from src.notifications.channel import TelegramChannel
        self.assertIsNotNone(TelegramChannel)

    def test_telegram_channel_is_telegram_stub(self):
        from src.notifications.channel import TelegramChannel, TelegramStub
        self.assertIs(TelegramChannel, TelegramStub)

    def test_telegram_channel_instantiates(self):
        from src.notifications.channel import TelegramChannel
        tg = TelegramChannel()
        self.assertIsNotNone(tg)

    def test_telegram_channel_name(self):
        from src.notifications.channel import TelegramChannel
        tg = TelegramChannel()
        self.assertEqual(tg.name(), "telegram")


# ── TelegramStub.send_text ────────────────────────────────────────────────────

class TestTelegramSendText(unittest.TestCase):

    def _env_without_telegram(self):
        return {k: v for k, v in os.environ.items()
                if k not in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")}

    def test_send_text_unavailable_returns_false(self):
        from src.notifications.channel import TelegramStub
        with patch.dict(os.environ, self._env_without_telegram(), clear=True):
            tg = TelegramStub()
            self.assertFalse(tg.send_text("teste"))

    def test_send_text_calls_api(self):
        from src.notifications.channel import TelegramStub
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "token123",
            "TELEGRAM_CHAT_ID": "456",
        }):
            tg = TelegramStub()
            with patch("src.notifications.channel.urlopen", return_value=mock_resp) as mock_open:
                result = tg.send_text("Olá!")
                self.assertTrue(result)
                mock_open.assert_called_once()

    def test_send_text_network_error_returns_false(self):
        from src.notifications.channel import TelegramStub
        from urllib.error import URLError
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "token123",
            "TELEGRAM_CHAT_ID": "456",
        }):
            tg = TelegramStub()
            with patch("src.notifications.channel.urlopen", side_effect=URLError("network")):
                self.assertFalse(tg.send_text("teste"))

    def test_send_text_status_non_200_returns_false(self):
        from src.notifications.channel import TelegramStub
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "token123",
            "TELEGRAM_CHAT_ID": "456",
        }):
            tg = TelegramStub()
            with patch("src.notifications.channel.urlopen", return_value=mock_resp):
                self.assertFalse(tg.send_text("teste"))


# ── TelegramStub.setup_hint ───────────────────────────────────────────────────

class TestTelegramSetupHint(unittest.TestCase):

    def test_setup_hint_returns_string(self):
        from src.notifications.channel import TelegramStub
        hint = TelegramStub.setup_hint()
        self.assertIsInstance(hint, str)
        self.assertGreater(len(hint), 20)

    def test_setup_hint_mentions_botfather(self):
        from src.notifications.channel import TelegramStub
        self.assertIn("BotFather", TelegramStub.setup_hint())

    def test_setup_hint_mentions_env_vars(self):
        from src.notifications.channel import TelegramStub
        hint = TelegramStub.setup_hint()
        self.assertIn("TELEGRAM_BOT_TOKEN", hint)
        self.assertIn("TELEGRAM_CHAT_ID", hint)


# ── TelegramStub.test_send ────────────────────────────────────────────────────

class TestTelegramTestSend(unittest.TestCase):

    def _env_without_telegram(self):
        return {k: v for k, v in os.environ.items()
                if k not in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")}

    def test_test_send_unavailable_returns_false(self):
        from src.notifications.channel import TelegramStub
        with patch.dict(os.environ, self._env_without_telegram(), clear=True):
            tg = TelegramStub()
            self.assertFalse(tg.test_send())

    def test_test_send_available_calls_send_text(self):
        from src.notifications.channel import TelegramStub
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "tok",
            "TELEGRAM_CHAT_ID": "123",
        }):
            tg = TelegramStub()
            with patch.object(tg, "send_text", return_value=True) as mock_st:
                result = tg.test_send()
                self.assertTrue(result)
                mock_st.assert_called_once()


# ── ProactiveDelivery ─────────────────────────────────────────────────────────

class TestProactiveDelivery(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)

    def tearDown(self):
        import gc; gc.collect()
        self.tmp.cleanup()

    def _make_monitor_no_alerts(self):
        from src.scheduler.proactive import ProactiveMonitor
        backup_path = os.path.join(self.tmp.name, "backups")
        os.makedirs(backup_path, exist_ok=True)
        with zipfile.ZipFile(os.path.join(backup_path, "wind_backup_test.zip"), "w") as z:
            z.writestr("test.txt", "ok")
        return ProactiveMonitor(
            db_path=os.path.join(self.tmp.name, "wind.db"),
            backup_dir=backup_path,
        )

    def test_run_no_alerts_returns_zero(self):
        from src.scheduler.delivery import ProactiveDelivery
        monitor = self._make_monitor_no_alerts()
        manager = MagicMock()
        delivery = ProactiveDelivery(monitor, manager)
        self.assertEqual(delivery.run(), 0)

    def test_run_no_alerts_does_not_call_manager(self):
        from src.scheduler.delivery import ProactiveDelivery
        monitor = self._make_monitor_no_alerts()
        manager = MagicMock()
        delivery = ProactiveDelivery(monitor, manager)
        delivery.run()
        manager.warning.assert_not_called()

    def test_run_with_alerts_calls_manager_warning(self):
        from src.scheduler.delivery import ProactiveDelivery
        from src.scheduler.proactive import ProactiveAlert
        monitor = MagicMock()
        monitor.check_all.return_value = [
            ProactiveAlert(type="backup_overdue", message="Backup vencido", severity="warning")
        ]
        monitor.format_alerts.return_value = "⚠️ Backup vencido"
        manager = MagicMock()
        delivery = ProactiveDelivery(monitor, manager)
        count = delivery.run()
        self.assertEqual(count, 1)
        manager.warning.assert_called_once()

    def test_run_with_multiple_alerts_returns_correct_count(self):
        from src.scheduler.delivery import ProactiveDelivery
        from src.scheduler.proactive import ProactiveAlert
        monitor = MagicMock()
        monitor.check_all.return_value = [
            ProactiveAlert(type="a", message="x", severity="info"),
            ProactiveAlert(type="b", message="y", severity="warning"),
            ProactiveAlert(type="c", message="z", severity="critical"),
        ]
        monitor.format_alerts.return_value = "..."
        manager = MagicMock()
        delivery = ProactiveDelivery(monitor, manager)
        self.assertEqual(delivery.run(), 3)

    def test_run_and_report_no_alerts_returns_ok_message(self):
        from src.scheduler.delivery import ProactiveDelivery
        monitor = self._make_monitor_no_alerts()
        manager = MagicMock()
        delivery = ProactiveDelivery(monitor, manager)
        text = delivery.run_and_report()
        self.assertIn("Nenhum", text)

    def test_run_and_report_no_alerts_does_not_deliver(self):
        from src.scheduler.delivery import ProactiveDelivery
        monitor = self._make_monitor_no_alerts()
        manager = MagicMock()
        delivery = ProactiveDelivery(monitor, manager)
        delivery.run_and_report()
        manager.warning.assert_not_called()

    def test_run_and_report_with_alerts_delivers_and_returns(self):
        from src.scheduler.delivery import ProactiveDelivery
        from src.scheduler.proactive import ProactiveAlert
        monitor = MagicMock()
        monitor.check_all.return_value = [
            ProactiveAlert(type="backup_overdue", message="Backup!", severity="critical")
        ]
        monitor.format_alerts.return_value = "🚨 Backup!"
        manager = MagicMock()
        delivery = ProactiveDelivery(monitor, manager)
        text = delivery.run_and_report()
        self.assertEqual(text, "🚨 Backup!")
        manager.warning.assert_called_once()

    def test_channels_active_delegates_to_manager(self):
        from src.scheduler.delivery import ProactiveDelivery
        monitor = MagicMock()
        manager = MagicMock()
        manager.available_channels.return_value = ["console", "file"]
        delivery = ProactiveDelivery(monitor, manager)
        self.assertEqual(delivery.channels_active(), ["console", "file"])

    def test_delivery_exported_from_scheduler_package(self):
        from src.scheduler import ProactiveDelivery
        self.assertIsNotNone(ProactiveDelivery)


# ── Integração: NotificationManager inclui TelegramStub ──────────────────────

class TestNotificationManagerHasTelegram(unittest.TestCase):

    def _env_without_telegram(self):
        return {k: v for k, v in os.environ.items()
                if k not in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")}

    def test_manager_has_telegram_channel(self):
        from src.notifications.manager import NotificationManager
        mgr = NotificationManager()
        types = [type(c).__name__ for c in mgr._channels]
        self.assertIn("TelegramStub", types)

    def test_available_channels_without_env(self):
        from src.notifications.manager import NotificationManager
        with patch.dict(os.environ, self._env_without_telegram(), clear=True):
            mgr = NotificationManager()
            self.assertNotIn("telegram", mgr.available_channels())

    def test_available_channels_with_env(self):
        from src.notifications.manager import NotificationManager
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "token123",
            "TELEGRAM_CHAT_ID": "456",
        }):
            mgr = NotificationManager()
            self.assertIn("telegram", mgr.available_channels())


if __name__ == "__main__":
    unittest.main(verbosity=2)
