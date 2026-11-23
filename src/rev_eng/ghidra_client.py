"""
GhidraClient — interface para o Ghidra headless analyzer.
Executa análise em processo separado, lê o output e retorna estruturado.
Nunca executa fora de WIND_RE_WORKDIR.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


GHIDRA_PATH   = Path(os.getenv("GHIDRA_PATH", r"C:\Users\Repro\Documents\ghidra_12.1.4_PUBLIC"))
WORK_ROOT     = Path(os.getenv("WIND_RE_WORKDIR", "data/re_workspace"))
GHIDRA_HEADLESS = GHIDRA_PATH / "support" / "analyzeHeadless"


@dataclass
class GhidraResult:
    success: bool
    job_id: str
    duration_s: float
    stdout: str = ""
    stderr: str = ""
    project_path: Optional[str] = None
    error: Optional[str] = None

    def has_analysis(self) -> bool:
        return self.success and bool(self.project_path)


def _find_headless(ghidra_root: Optional[Path] = None) -> Optional[Path]:
    """
    Localiza o script analyzeHeadless na instalação do Ghidra.
    Tenta vários layouts: release (support/), source, variantes de path.
    """
    root = ghidra_root or GHIDRA_PATH
    candidates: list[Path] = [
        root / "support" / "analyzeHeadless.bat",
        root / "support" / "analyzeHeadless",
        root / "analyzeHeadless.bat",
        root / "analyzeHeadless",
        root / "ghidra" / "support" / "analyzeHeadless.bat",
        root / "ghidra" / "support" / "analyzeHeadless",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def validate_ghidra_install(ghidra_root: Path = GHIDRA_PATH) -> dict:
    """
    Valida a instalação do Ghidra e retorna diagnóstico detalhado.
    Retorna dict com 'ok', 'headless', 'processors_ok', 'message', 'install_hint'.
    """
    result: dict = {
        "ok": False,
        "root_exists": ghidra_root.exists(),
        "headless": None,
        "processors_ok": False,
        "message": "",
        "install_hint": (
            "Para instalar o Ghidra (release):\n"
            "  1. Baixe em https://ghidra-sre.org/\n"
            "  2. Extraia em C:\\Users\\Repro\\Documents\\ghidra_<versao>_PUBLIC\\\n"
            "  3. Verifique que a pasta support\\analyzeHeadless.bat existe\n"
            "  4. Configure GHIDRA_PATH se necessário:\n"
            "       setx GHIDRA_PATH \"C:\\seu\\caminho\\ghidra_12.x_PUBLIC\"\n"
        ),
    }
    if not ghidra_root.exists():
        result["message"] = f"Diretório não encontrado: {ghidra_root}"
        return result

    # Verifica se é um release (tem support/)
    support_dir = ghidra_root / "support"
    headless = _find_headless(ghidra_root)
    result["headless"] = str(headless) if headless else None
    result["ok"] = headless is not None

    # Verifica processadores TriCore (essencial para ECUs do acervo)
    proc_dir = ghidra_root / "Ghidra" / "Processors"
    result["processors_ok"] = proc_dir.exists()
    tricore_ok = (proc_dir / "tricore").exists() if proc_dir.exists() else False
    powerpc_ok = (proc_dir / "PowerPC").exists() if proc_dir.exists() else False

    if headless:
        result["message"] = f"Ghidra OK: {headless}"
        if tricore_ok:
            result["message"] += " | TriCore ✅"
        if powerpc_ok:
            result["message"] += " | PowerPC ✅"
    else:
        dirs_found = [d.name for d in ghidra_root.iterdir() if d.is_dir()] if ghidra_root.exists() else []
        if support_dir.exists():
            result["message"] = (
                f"Pasta support/ existe mas analyzeHeadless não foi encontrado.\n"
                f"Arquivos em support/: {list(support_dir.iterdir())[:5]}"
            )
        else:
            result["message"] = (
                f"Instalação sem support/ (provável build de desenvolvimento, não release).\n"
                f"Pastas encontradas: {dirs_found}\n"
                f"Baixe o release oficial em https://ghidra-sre.org/"
            )
    return result


class GhidraClient:
    """
    Wrapper para o Ghidra headless analyzer.
    Importa um binário ECU em um projeto temporário e executa análise automática.
    """

    def __init__(
        self,
        ghidra_root: Path = GHIDRA_PATH,
        work_root: Path = WORK_ROOT,
        timeout_s: int = 300,
    ) -> None:
        self._ghidra_root = ghidra_root
        self._work_root = work_root
        self._timeout_s = timeout_s
        self._headless: Optional[Path] = _find_headless(ghidra_root)

    @property
    def is_available(self) -> bool:
        return self._headless is not None and self._headless.exists()

    def analyze(
        self,
        binary_path: str | Path,
        job_id: str,
        language_id: str = "tricore:LE:32:default",
        pre_script: Optional[str] = None,
        post_script: Optional[str] = None,
    ) -> GhidraResult:
        """
        Importa e analisa um binário via Ghidra headless.
        language_id: ex. "tricore:LE:32:default", "PowerPC:BE:32:VLE"

        Requer que a instalação do Ghidra tenha a pasta support/analyzeHeadless.
        Se não disponível, retorna resultado de erro sem travar.
        """
        if not self.is_available:
            return GhidraResult(
                success=False,
                job_id=job_id,
                duration_s=0.0,
                error=(
                    f"analyzeHeadless não encontrado em {self._ghidra_root}. "
                    "Certifique-se que o Ghidra está instalado corretamente."
                ),
            )

        project_dir = self._work_root / job_id / "ghidra_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        project_name = f"wind_re_{job_id}"

        cmd = [
            str(self._headless),
            str(project_dir),
            project_name,
            "-import", str(binary_path),
            "-language", language_id,
            "-overwrite",
            "-noanalysis" if (pre_script or post_script) else "-analyze",
        ]
        if pre_script:
            cmd += ["-preScript", pre_script]
        if post_script:
            cmd += ["-postScript", post_script]

        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout_s,
                cwd=str(self._work_root / job_id),
            )
            duration = time.time() - t0
            return GhidraResult(
                success=proc.returncode == 0,
                job_id=job_id,
                duration_s=duration,
                stdout=proc.stdout[:8000],
                stderr=proc.stderr[:4000],
                project_path=str(project_dir / project_name) if proc.returncode == 0 else None,
                error=None if proc.returncode == 0 else f"Exit code {proc.returncode}",
            )
        except subprocess.TimeoutExpired:
            return GhidraResult(
                success=False, job_id=job_id, duration_s=self._timeout_s,
                error=f"Timeout após {self._timeout_s}s",
            )
        except Exception as exc:
            return GhidraResult(
                success=False, job_id=job_id, duration_s=time.time() - t0,
                error=str(exc),
            )

    def run_script(
        self,
        project_path: str | Path,
        script_path: str | Path,
        script_args: list[str] | None = None,
    ) -> GhidraResult:
        """Executa um script Ghidra em um projeto já importado."""
        if not self.is_available:
            return GhidraResult(
                success=False, job_id="script",
                duration_s=0.0, error="analyzeHeadless não disponível",
            )
        # Implementação completa quando analyzeHeadless estiver disponível
        return GhidraResult(
            success=False, job_id="script",
            duration_s=0.0, error="run_script não implementado nesta fase",
        )
