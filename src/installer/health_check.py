"""
Health check e checklist de Release Candidate da WIND — Fase 9.

Roda uma série de verificações e retorna um relatório estruturado.
Nunca modifica estado — somente lê e verifica.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    warning: bool = False   # aviso não-bloqueante

    def icon(self) -> str:
        if self.ok:
            return "✅"
        if self.warning:
            return "⚠️"
        return "❌"

    def line(self) -> str:
        icon = self.icon()
        detail = f" — {self.detail}" if self.detail else ""
        return f"  {icon} {self.name}{detail}"


@dataclass
class HealthReport:
    checks: list[CheckResult] = field(default_factory=list)

    def passed(self) -> int:
        return sum(1 for c in self.checks if c.ok)

    def failed(self) -> int:
        return sum(1 for c in self.checks if not c.ok and not c.warning)

    def warnings(self) -> int:
        return sum(1 for c in self.checks if c.warning and not c.ok)

    def rc_ready(self) -> bool:
        return self.failed() == 0

    def summary(self) -> str:
        lines = [
            f"=== WIND Health Check ===",
            f"{'RC APROVADO ✅' if self.rc_ready() else 'RC BLOQUEADO ❌'}  —  "
            f"{self.passed()} ok / {self.failed()} falhas / {self.warnings()} avisos",
            "",
        ]
        for c in self.checks:
            lines.append(c.line())
        return "\n".join(lines)


class HealthChecker:
    def __init__(self, root: Path | str = ".") -> None:
        self._root = Path(root)

    def run(self) -> HealthReport:
        report = HealthReport()
        checks = [
            self._check_python_version,
            self._check_required_modules,
            self._check_data_dir,
            self._check_db_exists,
            self._check_db_schema,
            self._check_env_anthropic,
            self._check_env_openai,
            self._check_env_wind_api_key,
            self._check_no_secrets_in_code,
            self._check_tests,
            self._check_docs,
            self._check_backup_dir,
        ]
        for fn in checks:
            try:
                result = fn()
            except Exception as e:
                result = CheckResult(fn.__name__, ok=False, detail=f"exceção: {e}")
            report.checks.append(result)
        return report

    # ── Verificações individuais ───────────────────────────────────────────

    def _check_python_version(self) -> CheckResult:
        major, minor = sys.version_info[:2]
        ok = (major, minor) >= (3, 10)
        return CheckResult(
            "Python >= 3.10", ok,
            detail=f"{major}.{minor}.{sys.version_info.micro}",
        )

    def _check_required_modules(self) -> CheckResult:
        required = ["sqlite3", "pathlib", "hashlib", "hmac", "json", "zipfile"]
        missing  = []
        for mod in required:
            try:
                importlib.import_module(mod)
            except ImportError:
                missing.append(mod)
        ok = len(missing) == 0
        return CheckResult(
            "Módulos stdlib obrigatórios", ok,
            detail=f"ausentes: {missing}" if missing else "todos presentes",
        )

    def _check_data_dir(self) -> CheckResult:
        data = self._root / "data"
        return CheckResult(
            "Diretório data/", data.exists(),
            detail=str(data) if not data.exists() else "presente",
        )

    def _check_db_exists(self) -> CheckResult:
        db = self._root / "data" / "wind.db"
        return CheckResult(
            "Banco data/wind.db", db.exists(),
            detail="ausente — rode install.py" if not db.exists() else "presente",
            warning=not db.exists(),
        )

    def _check_db_schema(self) -> CheckResult:
        db = self._root / "data" / "wind.db"
        if not db.exists():
            return CheckResult("Schema SQLite", ok=False, warning=True, detail="DB ausente")
        try:
            import sqlite3
            with sqlite3.connect(str(db)) as conn:
                tables = {r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()}
            required = {"episodic_memory", "projects", "missions", "decisions", "learning_notes"}
            missing  = required - tables
            ok = len(missing) == 0
            return CheckResult(
                "Schema SQLite", ok,
                detail=f"tabelas faltando: {missing}" if missing else f"{len(tables)} tabelas ok",
            )
        except Exception as e:
            return CheckResult("Schema SQLite", ok=False, detail=str(e))

    def _check_env_anthropic(self) -> CheckResult:
        import os
        key = os.getenv("ANTHROPIC_API_KEY", "")
        ok  = len(key) > 10 and not key.startswith("sk-ant-PLACEHOLDER")
        return CheckResult(
            "ANTHROPIC_API_KEY", ok,
            detail="configurada" if ok else "ausente ou placeholder",
            warning=not ok,
        )

    def _check_env_openai(self) -> CheckResult:
        import os
        key = os.getenv("OPENAI_API_KEY", "")
        ok  = len(key) > 10
        return CheckResult(
            "OPENAI_API_KEY", ok,
            detail="configurada" if ok else "ausente (fallback indisponível)",
            warning=not ok,
        )

    def _check_env_wind_api_key(self) -> CheckResult:
        import os
        key = os.getenv("WIND_API_KEY", "")
        ok  = len(key) >= 16
        return CheckResult(
            "WIND_API_KEY", ok,
            detail="configurada" if ok else "ausente — API HTTP desativada",
            warning=not ok,
        )

    def _check_no_secrets_in_code(self) -> CheckResult:
        """Verifica se nenhum arquivo Python contém padrões de chaves hardcoded."""
        import re
        patterns = [
            re.compile(r'sk-ant-api03-[A-Za-z0-9\-_]{20,}'),  # Anthropic key
            re.compile(r'sk-[A-Za-z0-9]{20,}'),               # OpenAI key
        ]
        found: list[str] = []
        for py in (self._root / "src").rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
                for pat in patterns:
                    if pat.search(text):
                        found.append(py.name)
                        break
            except OSError:
                continue
        ok = len(found) == 0
        return CheckResult(
            "Sem secrets hardcoded em src/", ok,
            detail=f"arquivos suspeitos: {found}" if found else "nenhum encontrado",
        )

    def _check_tests(self) -> CheckResult:
        """Roda pytest --co -q para contar testes (sem executar)."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/unit/", "--co", "-q", "--tb=no"],
                capture_output=True, text=True, timeout=30,
                cwd=str(self._root),
            )
            # Conta linhas que são IDs de teste (formato: "tests/unit/...")
            test_lines = [l for l in result.stdout.splitlines() if l.startswith("tests/")]
            count = len(test_lines)
            ok = count >= 300
            return CheckResult(
                "Testes unitários", ok,
                detail=f"{count} testes coletados {'(≥300 ✅)' if ok else '(<300 ⚠️)'}",
                warning=not ok,
            )
        except Exception as e:
            return CheckResult("Testes unitários", ok=False, detail=str(e))

    def _check_docs(self) -> CheckResult:
        required_docs = [
            "docs/WIND_MASTER_SPEC.md",
            "docs/WIND_IMPLEMENTATION_STATUS.md",
            "docs/WIND_ARCHITECTURE.md",
            "CLAUDE.md",
        ]
        missing = [d for d in required_docs if not (self._root / d).exists()]
        ok = len(missing) == 0
        return CheckResult(
            "Documentação obrigatória", ok,
            detail=f"faltando: {missing}" if missing else "toda presente",
        )

    def _check_backup_dir(self) -> CheckResult:
        bdir = self._root / "backups"
        ok   = bdir.exists()
        return CheckResult(
            "Diretório backups/", ok,
            detail="presente" if ok else "ausente — será criado no primeiro backup",
            warning=not ok,
        )
