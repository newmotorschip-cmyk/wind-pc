"""Testes da Fase 15 — AutoReporter + weekly_report seed."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ── AutoReporter._truncate ────────────────────────────────────────────────────

class TestAutoReporterTruncate(unittest.TestCase):

    def _truncate(self, text, limit=4000):
        from src.routines.reporter import AutoReporter
        return AutoReporter._truncate(text, limit=limit)

    def test_short_text_unchanged(self):
        text = "Olá, Felipe!"
        self.assertEqual(self._truncate(text), text)

    def test_exactly_limit_unchanged(self):
        text = "x" * 4000
        self.assertEqual(self._truncate(text), text)

    def test_over_limit_truncated_with_ellipsis(self):
        text = "x" * 5000
        result = self._truncate(text)
        self.assertEqual(len(result), 4000)
        self.assertTrue(result.endswith("..."))

    def test_custom_limit(self):
        text = "abcde"
        result = self._truncate(text, limit=4)
        self.assertEqual(result, "a...")

    def test_empty_string_unchanged(self):
        self.assertEqual(self._truncate(""), "")


# ── AutoReporter.send_morning_report ─────────────────────────────────────────

class TestAutoReporterMorningReport(unittest.TestCase):

    def _make(self, orc=None, manager=None):
        from src.routines.reporter import AutoReporter
        return AutoReporter(orc or MagicMock(), manager or MagicMock())

    def test_send_morning_report_calls_manager_info(self):
        manager = MagicMock()
        reporter = self._make(manager=manager)
        with patch("src.routines.morning.MorningSummary.generate", return_value="Resumo de teste"):
            reporter.send_morning_report()
        manager.info.assert_called_once()
        call_args = manager.info.call_args
        self.assertIn("Resumo", call_args[0][0])

    def test_send_morning_report_returns_text(self):
        manager = MagicMock()
        reporter = self._make(manager=manager)
        with patch("src.routines.morning.MorningSummary.generate", return_value="Texto do resumo"):
            result = reporter.send_morning_report()
        self.assertEqual(result, "Texto do resumo")

    def test_send_morning_report_truncates_long_text(self):
        manager = MagicMock()
        reporter = self._make(manager=manager)
        long_text = "x" * 5000
        with patch("src.routines.morning.MorningSummary.generate", return_value=long_text):
            result = reporter.send_morning_report()
        self.assertLessEqual(len(result), 4000)
        self.assertTrue(result.endswith("..."))

    def test_send_morning_report_passes_body_to_manager(self):
        manager = MagicMock()
        reporter = self._make(manager=manager)
        with patch("src.routines.morning.MorningSummary.generate", return_value="Resumo curto"):
            reporter.send_morning_report()
        _, body = manager.info.call_args[0]
        self.assertEqual(body, "Resumo curto")


# ── AutoReporter.send_weekly_report ──────────────────────────────────────────

class TestAutoReporterWeeklyReport(unittest.TestCase):

    def _make(self, orc=None, manager=None):
        from src.routines.reporter import AutoReporter
        return AutoReporter(orc or MagicMock(), manager or MagicMock())

    def test_send_weekly_report_calls_manager_info(self):
        manager = MagicMock()
        reporter = self._make(manager=manager)
        with patch("src.learning.retrospective.RetrospectiveGenerator.generate",
                   return_value="Retrospectiva teste"):
            reporter.send_weekly_report()
        manager.info.assert_called_once()

    def test_send_weekly_report_returns_text(self):
        manager = MagicMock()
        reporter = self._make(manager=manager)
        with patch("src.learning.retrospective.RetrospectiveGenerator.generate",
                   return_value="Retrospectiva semanal"):
            result = reporter.send_weekly_report()
        self.assertEqual(result, "Retrospectiva semanal")

    def test_send_weekly_report_truncates_long_text(self):
        manager = MagicMock()
        reporter = self._make(manager=manager)
        with patch("src.learning.retrospective.RetrospectiveGenerator.generate",
                   return_value="y" * 6000):
            result = reporter.send_weekly_report()
        self.assertLessEqual(len(result), 4000)

    def test_send_weekly_report_title_contains_semanal(self):
        manager = MagicMock()
        reporter = self._make(manager=manager)
        with patch("src.learning.retrospective.RetrospectiveGenerator.generate",
                   return_value="Texto"):
            reporter.send_weekly_report()
        title = manager.info.call_args[0][0]
        self.assertIn("Semanal", title)


# ── AutoReporter.channels_active ─────────────────────────────────────────────

class TestAutoReporterChannels(unittest.TestCase):

    def test_channels_active_delegates_to_manager(self):
        from src.routines.reporter import AutoReporter
        manager = MagicMock()
        manager.available_channels.return_value = ["console", "telegram"]
        reporter = AutoReporter(MagicMock(), manager)
        self.assertEqual(reporter.channels_active(), ["console", "telegram"])

    def test_auto_reporter_exported_from_routines(self):
        from src.routines import AutoReporter
        self.assertIsNotNone(AutoReporter)


# ── WindScheduler — weekly_report seed ───────────────────────────────────────

class TestWeeklyReportSeed(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "wind.db")

    def tearDown(self):
        import gc; gc.collect()
        self.tmp.cleanup()

    def _make(self):
        from src.scheduler.scheduler import WindScheduler
        return WindScheduler(db_path=self.db)

    def test_weekly_report_task_seeded(self):
        s = self._make()
        ids = [t.id for t in s.list_tasks()]
        self.assertIn("weekly_report", ids)

    def test_weekly_report_schedule_is_weekly(self):
        s = self._make()
        task = s.get_task("weekly_report")
        self.assertIsNotNone(task)
        self.assertTrue(task.schedule.startswith("weekly@"))

    def test_weekly_report_handler_name(self):
        s = self._make()
        task = s.get_task("weekly_report")
        self.assertEqual(task.handler, "weekly_report")

    def test_weekly_report_enabled_by_default(self):
        s = self._make()
        task = s.get_task("weekly_report")
        self.assertTrue(task.enabled)

    def test_seed_now_has_four_default_tasks(self):
        s = self._make()
        self.assertEqual(len(s.list_tasks()), 4)

    def test_summary_contains_relatorio_semanal(self):
        s = self._make()
        self.assertIn("Relatório semanal", s.summary())

    def test_seed_still_idempotent_with_four_tasks(self):
        s1 = self._make()
        s2 = self._make()
        self.assertEqual(len(s1.list_tasks()), len(s2.list_tasks()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
