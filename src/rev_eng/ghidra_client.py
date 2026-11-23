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


def _find_headless() -> Optional[Path]:
    """Localiza o analyzeHeadless na instalação do Ghidra."""
    candidates = [
        GHIDRA_PATH / "support" / "analyzeHeadless.bat",
        GHIDRA_PATH / "support" / "analyzeHeadless",
        GHIDRA_PATH / "analyzeHeadless.bat",
        GHIDRA_PATH / "analyzeHeadless",
    ]
    # Em Windows 10 o Ghidra 12.x não tem a pasta support — tenta via ghidraRun
    ghidra_run_candidates = [
        GHIDRA_PATH / "ghidraRun.bat",
        GHIDRA_PATH / "ghidra.bat",
    ]
    for c in candidates + ghidra_run_candidates:
        if c.exists():
            return c
    return None


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
        self._headless: Optional[Path] = _find_headless()

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
