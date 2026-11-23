"""Testes da Fase 9 — instalador, backup, migração e health check."""
import sys
from pathlib import Path

import pytest

from src.installer.backup import BackupManager, BackupInfo
from src.installer.updater import Migrator, MIGRATIONS
from src.installer.health_check import HealthChecker, HealthReport, CheckResult


# ── BackupManager ──────────────────────────────────────────────────────────

@pytest.fixture
def backup_root(tmp_path):
    """Cria uma estrutura mínima de arquivos para testar backup."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "wind.db").write_bytes(b"SQLite placeholder")
    (data / "autonomy_profile.json").write_text('{"current_level":"A1"}', encoding="utf-8")
    return tmp_path


def test_backup_create(backup_root):
    mgr  = BackupManager(backup_root)
    info = mgr.create()
    assert info.path.exists()
    assert info.size_bytes > 0
    assert "data/wind.db" in info.files_included


def test_backup_create_with_label(backup_root):
    mgr  = BackupManager(backup_root)
    info = mgr.create(label="pre_test")
    assert "pre_test" in info.path.name


def test_backup_list(backup_root):
    mgr = BackupManager(backup_root)
    mgr.create(label="b1")
    mgr.create(label="b2")
    backups = mgr.list()
    assert len(backups) >= 2


def test_backup_list_empty(tmp_path):
    mgr = BackupManager(tmp_path)
    assert mgr.list() == []


def test_backup_info_label(backup_root):
    mgr  = BackupManager(backup_root)
    info = mgr.create()
    label = info.label()
    assert "wind_backup_" in label
    assert "KB" in label


def test_backup_to_dict(backup_root):
    mgr  = BackupManager(backup_root)
    info = mgr.create()
    d    = info.to_dict()
    assert "path" in d
    assert "files_included" in d


def test_backup_restore(backup_root):
    mgr  = BackupManager(backup_root)
    info = mgr.create()

    # Corrompe o arquivo
    db = backup_root / "data" / "wind.db"
    db.write_bytes(b"CORRUPTED")
    assert db.read_bytes() == b"CORRUPTED"

    # Restaura
    restored = mgr.restore(info.path)
    assert "data/wind.db" in restored
    assert db.read_bytes() == b"SQLite placeholder"


def test_backup_restore_missing_file(tmp_path):
    mgr = BackupManager(tmp_path)
    with pytest.raises(FileNotFoundError):
        mgr.restore(tmp_path / "nonexistent.zip")


def test_backup_rotation(backup_root):
    """Backups além de _MAX_BACKUPS devem ser removidos."""
    from src.installer.backup import _MAX_BACKUPS
    mgr = BackupManager(backup_root)
    for i in range(_MAX_BACKUPS + 5):
        mgr.create(label=f"rot{i}")
    backups = list((backup_root / "backups").glob("wind_backup_*.zip"))
    assert len(backups) <= _MAX_BACKUPS


def test_backup_skips_missing_files(tmp_path):
    """Arquivos ausentes não devem causar erro — apenas são omitidos."""
    (tmp_path / "data").mkdir()
    mgr  = BackupManager(tmp_path)
    info = mgr.create()
    # data/wind.db não existe — incluídos só os que existem
    assert "data/wind.db" not in info.files_included


# ── Migrator ───────────────────────────────────────────────────────────────

@pytest.fixture
def migrator(tmp_path):
    return Migrator(tmp_path / "test.db")


def test_migrator_initial_version(migrator):
    assert migrator.current_version() == 0


def test_migrator_migrate_all(migrator):
    applied = migrator.migrate()
    assert len(applied) == len(MIGRATIONS)
    assert migrator.current_version() == MIGRATIONS[-1].version


def test_migrator_idempotent(migrator):
    migrator.migrate()
    applied_again = migrator.migrate()
    assert applied_again == []
    assert migrator.current_version() == MIGRATIONS[-1].version


def test_migrator_pending(migrator):
    pending = migrator.pending()
    assert len(pending) == len(MIGRATIONS)


def test_migrator_pending_after_migrate(migrator):
    migrator.migrate()
    pending = migrator.pending()
    assert pending == []


def test_migrator_status(migrator):
    status = migrator.status()
    assert status["current_version"] == 0
    assert status["pending_count"] == len(MIGRATIONS)
    assert status["up_to_date"] is False


def test_migrator_status_after_migrate(migrator):
    migrator.migrate()
    status = migrator.status()
    assert status["up_to_date"] is True
    assert status["pending_count"] == 0


def test_migrator_creates_tables(migrator):
    import sqlite3
    migrator.migrate()
    with sqlite3.connect(str(migrator._path)) as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "decisions" in tables
    assert "learning_notes" in tables
    assert "episodic_memory" in tables
    assert "service_cases" in tables


def test_migrator_service_cases_has_created_at(migrator):
    """Migração 5 deve criar service_cases com created_at (não opened_at)."""
    import sqlite3
    migrator.migrate()
    with sqlite3.connect(str(migrator._path)) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(service_cases)").fetchall()}
    assert "created_at" in cols
    assert "hypotheses" in cols
    assert "time_minutes" in cols
    assert "opened_at" not in cols  # schema antigo não deve estar presente


def test_migrator_schema_version_table(migrator):
    import sqlite3
    migrator.migrate()
    with sqlite3.connect(str(migrator._path)) as conn:
        rows = conn.execute("SELECT version FROM schema_version ORDER BY version").fetchall()
    versions = [r[0] for r in rows]
    assert versions == list(range(1, len(MIGRATIONS) + 1))


def test_migrator_no_data_loss_on_rerun(migrator):
    """Rodar migrate duas vezes não deve apagar dados."""
    import sqlite3, time
    migrator.migrate()
    with sqlite3.connect(str(migrator._path)) as conn:
        conn.execute(
            "INSERT INTO decisions (id,request,options,evidence,risk,reversible,confidence,"
            "chosen_option,approved_by,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("test-id","r","[]","e","low",1,0.9,"A","","pending", time.time())
        )
    migrator.migrate()
    with sqlite3.connect(str(migrator._path)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    assert count == 1


# ── CheckResult / HealthReport ─────────────────────────────────────────────

def test_check_result_ok_icon():
    c = CheckResult("teste", ok=True)
    assert c.icon() == "✅"


def test_check_result_fail_icon():
    c = CheckResult("teste", ok=False)
    assert c.icon() == "❌"


def test_check_result_warning_icon():
    c = CheckResult("teste", ok=False, warning=True)
    assert c.icon() == "⚠️"


def test_health_report_counts():
    report = HealthReport(checks=[
        CheckResult("a", ok=True),
        CheckResult("b", ok=False),
        CheckResult("c", ok=False, warning=True),
    ])
    assert report.passed() == 1
    assert report.failed() == 1
    assert report.warnings() == 1


def test_health_report_rc_ready_no_failures():
    report = HealthReport(checks=[
        CheckResult("a", ok=True),
        CheckResult("b", ok=False, warning=True),  # warning não bloqueia RC
    ])
    assert report.rc_ready() is True


def test_health_report_rc_blocked():
    report = HealthReport(checks=[
        CheckResult("a", ok=True),
        CheckResult("b", ok=False),
    ])
    assert report.rc_ready() is False


def test_health_report_summary_contains_status():
    report = HealthReport(checks=[CheckResult("x", ok=True)])
    summary = report.summary()
    assert "Health Check" in summary


# ── HealthChecker ──────────────────────────────────────────────────────────

@pytest.fixture
def checker(tmp_path):
    # Cria estrutura mínima para checks não falharem por ausência de dirs
    (tmp_path / "data").mkdir()
    (tmp_path / "docs").mkdir()
    for doc in ["WIND_MASTER_SPEC.md", "WIND_IMPLEMENTATION_STATUS.md",
                "WIND_ARCHITECTURE.md"]:
        (tmp_path / "docs" / doc).write_text("placeholder", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("placeholder", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "unit").mkdir()
    return HealthChecker(tmp_path)


def test_checker_run_returns_report(checker):
    report = checker.run()
    assert isinstance(report, HealthReport)
    assert len(report.checks) >= 5


def test_checker_python_version(checker):
    report = checker.run()
    py_check = next((c for c in report.checks if "Python" in c.name), None)
    assert py_check is not None
    # Python atual deve ser >= 3.10
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 10):
        assert py_check.ok is True


def test_checker_no_secrets_in_empty_src(checker):
    report = checker.run()
    secrets_check = next((c for c in report.checks if "secrets" in c.name.lower()), None)
    assert secrets_check is not None
    assert secrets_check.ok is True


def test_checker_secrets_detected(tmp_path):
    """Deve detectar chave Anthropic hardcoded em código."""
    src = tmp_path / "src"
    src.mkdir()
    # Coloca uma chave fake com o padrão real
    (src / "bad.py").write_text(
        'API_KEY = "sk-ant-api03-' + 'A' * 30 + '"',
        encoding="utf-8",
    )
    chk = HealthChecker(tmp_path)
    report = chk.run()
    sec = next((c for c in report.checks if "secrets" in c.name.lower()), None)
    assert sec is not None
    assert sec.ok is False


def test_checker_docs_check(checker):
    report = checker.run()
    docs_check = next((c for c in report.checks if "Documentação" in c.name), None)
    assert docs_check is not None
    assert docs_check.ok is True


def test_checker_docs_missing(tmp_path):
    chk = HealthChecker(tmp_path)
    report = chk.run()
    docs_check = next((c for c in report.checks if "Documentação" in c.name), None)
    assert docs_check is not None
    assert docs_check.ok is False
