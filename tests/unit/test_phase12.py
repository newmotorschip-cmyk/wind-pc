"""Testes da Fase 12 — WindScheduler + ProactiveMonitor."""
from __future__ import annotations

import os
import sys
import sqlite3
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ── ScheduledTask ──────────────────────────────────────────────────────────────

class TestScheduledTask(unittest.TestCase):

    def test_to_dict_round_trip(self):
        from src.scheduler.scheduler import ScheduledTask
        t = ScheduledTask(id="t1", name="Teste", handler="backup", schedule="daily@07:00")
        d = t.to_dict()
        t2 = ScheduledTask.from_row((
            d["id"], d["name"], d["handler"], d["schedule"],
            d["params"], d["enabled"], d["last_run"], d["next_run"],
        ))
        self.assertEqual(t2.id, "t1")
        self.assertEqual(t2.name, "Teste")
        self.assertEqual(t2.handler, "backup")
        self.assertEqual(t2.schedule, "daily@07:00")

    def test_default_enabled(self):
        from src.scheduler.scheduler import ScheduledTask
        t = ScheduledTask(id="x", name="X", handler="h", schedule="interval@60")
        self.assertTrue(t.enabled)

    def test_default_params_empty(self):
        from src.scheduler.scheduler import ScheduledTask
        t = ScheduledTask(id="x", name="X", handler="h", schedule="interval@60")
        self.assertEqual(t.params, {})


# ── _compute_next_run ─────────────────────────────────────────────────────────

class TestComputeNextRun(unittest.TestCase):

    def test_daily_future(self):
        from src.scheduler.scheduler import _compute_next_run
        base = datetime(2026, 11, 23, 6, 0, 0)
        result = _compute_next_run("daily@07:00", base)
        self.assertEqual(result.hour, 7)
        self.assertEqual(result.date(), base.date())

    def test_daily_past_moves_to_tomorrow(self):
        from src.scheduler.scheduler import _compute_next_run
        base = datetime(2026, 11, 23, 9, 0, 0)
        result = _compute_next_run("daily@08:00", base)
        self.assertEqual(result.date(), (base + timedelta(days=1)).date())
        self.assertEqual(result.hour, 8)

    def test_interval(self):
        from src.scheduler.scheduler import _compute_next_run
        base = datetime(2026, 11, 23, 10, 0, 0)
        result = _compute_next_run("interval@3600", base)
        self.assertEqual(int((result - base).total_seconds()), 3600)

    def test_weekly(self):
        from src.scheduler.scheduler import _compute_next_run
        # 2026-11-23 is a Monday (weekday=0)
        base = datetime(2026, 11, 23, 8, 0, 0)
        result = _compute_next_run("weekly@wed@09:00", base)
        self.assertEqual(result.weekday(), 2)  # Wednesday
        self.assertEqual(result.hour, 9)

    def test_weekly_same_day_past_moves_to_next_week(self):
        from src.scheduler.scheduler import _compute_next_run
        base = datetime(2026, 11, 23, 10, 0, 0)  # Monday 10:00
        result = _compute_next_run("weekly@mon@08:00", base)  # Monday 08:00 already passed
        self.assertEqual(result.weekday(), 0)  # Monday
        self.assertGreater(result, base + timedelta(days=5))

    def test_unknown_falls_back_to_one_hour(self):
        from src.scheduler.scheduler import _compute_next_run
        base = datetime(2026, 11, 23, 10, 0, 0)
        result = _compute_next_run("unknown@param", base)
        delta = int((result - base).total_seconds())
        self.assertAlmostEqual(delta, 3600, delta=5)


# ── WindScheduler ─────────────────────────────────────────────────────────────

class TestWindScheduler(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "wind.db")

    def tearDown(self):
        import gc; gc.collect()
        self.tmp.cleanup()

    def _make(self):
        from src.scheduler.scheduler import WindScheduler
        return WindScheduler(db_path=self.db)

    def test_init_creates_table(self):
        s = self._make()
        with sqlite3.connect(self.db) as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        self.assertIn("scheduled_tasks", tables)

    def test_default_tasks_seeded(self):
        s = self._make()
        ids = [t.id for t in s.list_tasks()]
        self.assertIn("backup_daily", ids)
        self.assertIn("morning_summary", ids)
        self.assertIn("proactive_check", ids)

    def test_seed_idempotent(self):
        s1 = self._make()
        s2 = self._make()
        self.assertEqual(len(s1.list_tasks()), len(s2.list_tasks()))

    def test_list_tasks_enabled_only(self):
        s = self._make()
        s.disable("backup_daily")
        enabled = s.list_tasks(enabled_only=True)
        ids = [t.id for t in enabled]
        self.assertNotIn("backup_daily", ids)
        self.assertIn("morning_summary", ids)

    def test_enable_disable(self):
        s = self._make()
        self.assertTrue(s.disable("backup_daily"))
        t = s.get_task("backup_daily")
        self.assertFalse(t.enabled)
        self.assertTrue(s.enable("backup_daily"))
        t = s.get_task("backup_daily")
        self.assertTrue(t.enabled)

    def test_enable_nonexistent_returns_false(self):
        s = self._make()
        self.assertFalse(s.enable("nao_existe_xyz"))

    def test_run_now_calls_handler(self):
        s = self._make()
        called = []
        s.register_handler("backup", lambda: called.append(True))
        result = s.run_now("backup_daily")
        self.assertTrue(result)
        self.assertEqual(len(called), 1)

    def test_run_now_nonexistent_returns_false(self):
        s = self._make()
        self.assertFalse(s.run_now("nao_existe_xyz"))

    def test_run_now_updates_last_run(self):
        s = self._make()
        s.register_handler("backup", lambda: None)
        s.run_now("backup_daily")
        t = s.get_task("backup_daily")
        self.assertIsNotNone(t.last_run)

    def test_run_now_handler_exception_does_not_raise(self):
        s = self._make()

        def bad_handler():
            raise RuntimeError("falha simulada")

        s.register_handler("backup", bad_handler)
        try:
            s.run_now("backup_daily")
        except RuntimeError:
            self.fail("run_now levantou exceção do handler")

    def test_add_custom_task(self):
        from src.scheduler.scheduler import ScheduledTask
        s = self._make()
        t = ScheduledTask(id="custom1", name="Meu teste", handler="proactive",
                          schedule="interval@120")
        s.add_task(t)
        result = s.get_task("custom1")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Meu teste")

    def test_add_task_auto_generates_id(self):
        from src.scheduler.scheduler import ScheduledTask
        s = self._make()
        t = ScheduledTask(id="", name="Sem ID", handler="backup", schedule="interval@60")
        saved = s.add_task(t)
        self.assertTrue(len(saved.id) > 0)

    def test_check_missed_runs_overdue(self):
        s = self._make()
        called = []
        s.register_handler("backup", lambda: called.append(True))
        # Coloca next_run no passado
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE scheduled_tasks SET next_run=? WHERE id='backup_daily'",
                (past,),
            )
            conn.commit()
        count = s.check_missed()
        self.assertGreater(count, 0)
        self.assertEqual(len(called), 1)

    def test_check_missed_skips_future(self):
        s = self._make()
        called = []
        s.register_handler("backup", lambda: called.append(True))
        # Garante que next_run é no futuro
        future = (datetime.now() + timedelta(hours=5)).isoformat()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE scheduled_tasks SET next_run=? WHERE id='backup_daily'",
                (future,),
            )
            conn.commit()
        count = s.check_missed()
        self.assertEqual(len(called), 0)

    def test_summary_contains_task_names(self):
        s = self._make()
        text = s.summary()
        self.assertIn("Backup diário", text)
        self.assertIn("Resumo matinal", text)

    def test_start_stop(self):
        s = self._make()
        s.start()
        self.assertTrue(s._running)
        s.stop()
        self.assertFalse(s._running)

    def test_start_idempotent(self):
        s = self._make()
        s.start()
        t1 = s._thread
        s.start()  # segunda chamada não deve criar novo thread
        self.assertIs(s._thread, t1)
        s.stop()


# ── ProactiveMonitor ──────────────────────────────────────────────────────────

class TestProactiveMonitor(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = os.path.join(self.tmp.name, "wind.db")
        self.backup_dir = os.path.join(self.tmp.name, "backups")

    def tearDown(self):
        import gc; gc.collect()
        self.tmp.cleanup()

    def _make(self):
        from src.scheduler.proactive import ProactiveMonitor
        return ProactiveMonitor(db_path=self.db, backup_dir=self.backup_dir)

    def test_no_alerts_on_missing_db(self):
        m = self._make()
        self.assertEqual(m.check_projects(), [])
        self.assertEqual(m.check_cases(), [])

    def test_check_all_returns_list(self):
        m = self._make()
        alerts = m.check_all()
        self.assertIsInstance(alerts, list)

    def test_format_alerts_empty(self):
        m = self._make()
        text = m.format_alerts([])
        self.assertIn("Nenhum", text)

    def test_format_alerts_with_items(self):
        from src.scheduler.proactive import ProactiveAlert
        m = self._make()
        alerts = [ProactiveAlert(type="project_stale", message="X parado.", severity="warning")]
        text = m.format_alerts(alerts)
        self.assertIn("project_stale", text)
        self.assertIn("X parado", text)

    def test_format_alerts_severity_icons(self):
        from src.scheduler.proactive import ProactiveAlert
        m = self._make()
        alerts = [
            ProactiveAlert(type="a", message="info", severity="info"),
            ProactiveAlert(type="b", message="crit", severity="critical"),
        ]
        text = m.format_alerts(alerts)
        self.assertIn("ℹ️", text)
        self.assertIn("🚨", text)

    def test_check_backup_no_dir(self):
        m = self._make()
        alerts = m.check_backup()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "backup_overdue")

    def test_check_backup_no_files(self):
        os.makedirs(self.backup_dir)
        m = self._make()
        alerts = m.check_backup()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "backup_overdue")

    def test_check_backup_recent_ok(self):
        os.makedirs(self.backup_dir)
        zip_path = os.path.join(self.backup_dir, "wind_backup_2026-11-23.zip")
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("test.txt", "ok")
        m = self._make()
        alerts = m.check_backup(max_age_days=7)
        self.assertEqual(len(alerts), 0)

    def test_check_project_stale(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "CREATE TABLE projects (id TEXT, name TEXT, status TEXT, updated_at TEXT)"
            )
            old = (datetime.now() - timedelta(days=10)).isoformat()
            conn.execute("INSERT INTO projects VALUES ('p1','Proj Velho','active',?)", (old,))
            conn.commit()
        m = self._make()
        alerts = m.check_projects(stale_days=7)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "project_stale")

    def test_check_project_fresh_no_alert(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "CREATE TABLE projects (id TEXT, name TEXT, status TEXT, updated_at TEXT)"
            )
            recent = datetime.now().isoformat()
            conn.execute("INSERT INTO projects VALUES ('p1','Proj Novo','active',?)", (recent,))
            conn.commit()
        m = self._make()
        alerts = m.check_projects(stale_days=7)
        self.assertEqual(len(alerts), 0)

    def test_check_case_stale(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "CREATE TABLE service_cases "
                "(id TEXT, vehicle_desc TEXT, status TEXT, created_at TEXT)"
            )
            old = (datetime.now() - timedelta(days=35)).isoformat()
            conn.execute("INSERT INTO service_cases VALUES ('c1','VW Gol','open',?)", (old,))
            conn.commit()
        m = self._make()
        alerts = m.check_cases(stale_days=30)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "case_stale")

    def test_check_case_fresh_no_alert(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "CREATE TABLE service_cases "
                "(id TEXT, vehicle_desc TEXT, status TEXT, created_at TEXT)"
            )
            recent = datetime.now().isoformat()
            conn.execute("INSERT INTO service_cases VALUES ('c1','VW Gol','open',?)", (recent,))
            conn.commit()
        m = self._make()
        alerts = m.check_cases(stale_days=30)
        self.assertEqual(len(alerts), 0)

    def test_check_budget_returns_list(self):
        m = self._make()
        alerts = m.check_budget()
        self.assertIsInstance(alerts, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
