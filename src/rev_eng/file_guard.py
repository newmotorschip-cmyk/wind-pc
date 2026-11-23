"""
FileGuard — proteção de arquivos originais no pipeline de engenharia reversa.
Regra: o original NUNCA é modificado. Sempre work em cópia verificada por hash.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import stat
import time
from dataclasses import dataclass
from pathlib import Path


WORK_ROOT = Path(os.getenv("WIND_RE_WORKDIR", "data/re_workspace"))


@dataclass
class FileRecord:
    original_path: str
    work_path: str
    sha256: str
    size_bytes: int
    created_at: float

    def verify(self) -> bool:
        """Verifica integridade do arquivo de trabalho contra o hash original."""
        return _sha256(Path(self.work_path)) == self.sha256

    def to_dict(self) -> dict:
        return {
            "original_path": self.original_path,
            "work_path": self.work_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
        }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_readonly(path: Path) -> None:
    """Torna o arquivo somente leitura no Windows/Linux."""
    current = path.stat().st_mode
    path.chmod(current & ~(stat.S_IWRITE | stat.S_IWGRP | stat.S_IWOTH))


class FileGuard:
    """
    Gerencia cópias de trabalho de arquivos ECU.
    - Original: nunca modificado, registrado com hash SHA-256.
    - Work copy: cópia em WORK_ROOT, integridade verificável a qualquer momento.
    """

    def __init__(self, work_root: Path = WORK_ROOT) -> None:
        self._work_root = work_root
        self._work_root.mkdir(parents=True, exist_ok=True)

    def protect(self, source_path: str | Path, job_id: str = "") -> FileRecord:
        """
        Registra o arquivo original (hash) e cria uma cópia de trabalho.
        O original NÃO é copiado como read-only para não bloquear o acervo do Felipe.
        A cópia de trabalho sim fica read-only após a cópia.
        """
        src = Path(source_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {src}")

        sha = _sha256(src)
        job_dir = self._work_root / (job_id or sha[:12])
        job_dir.mkdir(parents=True, exist_ok=True)

        dst = job_dir / src.name
        shutil.copy2(src, dst)
        _make_readonly(dst)

        record = FileRecord(
            original_path=str(src),
            work_path=str(dst),
            sha256=sha,
            size_bytes=src.stat().st_size,
            created_at=time.time(),
        )
        # Salva o hash em um sidecar
        (job_dir / f"{src.name}.sha256").write_text(f"{sha}  {src.name}\n", encoding="utf-8")
        return record

    def verify_original(self, record: FileRecord) -> bool:
        """Verifica se o original não foi modificado desde o registro."""
        try:
            return _sha256(Path(record.original_path)) == record.sha256
        except FileNotFoundError:
            return False

    def open_work_copy(self, record: FileRecord) -> bytes:
        """Lê o conteúdo da cópia de trabalho após verificar integridade."""
        if not record.verify():
            raise ValueError(f"Integridade violada: {record.work_path}")
        return Path(record.work_path).read_bytes()

    def cleanup_job(self, job_id: str) -> None:
        """Remove a pasta de trabalho de um job."""
        job_dir = self._work_root / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir)
