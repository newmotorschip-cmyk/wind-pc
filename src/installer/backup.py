"""
Backup e restauração do estado da WIND — Fase 9.

Faz backup de:
  - data/wind.db (banco principal)
  - data/autonomy_profile.json
  - data/curriculum.json
  - .env.wind (variáveis de ambiente, se existir)

Armazena em backups/wind_backup_YYYYMMDD_HHMMSS.zip
"""
from __future__ import annotations

import json
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


_DEFAULT_FILES = [
    "data/wind.db",
    "data/autonomy_profile.json",
    "data/curriculum.json",
    ".env.wind",
]

_MAX_BACKUPS = 20   # rotação automática


@dataclass
class BackupInfo:
    path: Path
    created_at: float
    size_bytes: int
    files_included: list[str]

    def label(self) -> str:
        dt  = datetime.fromtimestamp(self.created_at).strftime("%d/%m/%Y %H:%M:%S")
        kb  = self.size_bytes / 1024
        return f"{self.path.name}  [{dt}  {kb:.0f} KB  {len(self.files_included)} arquivos]"

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "created_at": self.created_at,
            "size_bytes": self.size_bytes,
            "files_included": self.files_included,
        }


class BackupManager:
    def __init__(self, root: Path | str = ".") -> None:
        self._root    = Path(root)
        self._backups_dir = self._root / "backups"

    def create(self, label: str = "") -> BackupInfo:
        """Cria um backup ZIP com todos os arquivos de estado existentes."""
        self._backups_dir.mkdir(parents=True, exist_ok=True)

        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        name     = f"wind_backup_{ts}.zip" if not label else f"wind_backup_{ts}_{label[:20]}.zip"
        zip_path = self._backups_dir / name

        included: list[str] = []
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for rel in _DEFAULT_FILES:
                src = self._root / rel
                if src.exists():
                    zf.write(src, rel)
                    included.append(rel)
            # Metadado de backup
            meta = json.dumps({
                "created_at": time.time(),
                "files": included,
                "label": label,
            }, indent=2, ensure_ascii=False)
            zf.writestr("backup_meta.json", meta)

        self._rotate()

        return BackupInfo(
            path=zip_path,
            created_at=time.time(),
            size_bytes=zip_path.stat().st_size,
            files_included=included,
        )

    def list(self) -> list[BackupInfo]:
        """Lista backups existentes, mais recente primeiro."""
        if not self._backups_dir.exists():
            return []
        result = []
        for zp in sorted(self._backups_dir.glob("wind_backup_*.zip"), reverse=True):
            try:
                with zipfile.ZipFile(zp, "r") as zf:
                    meta = json.loads(zf.read("backup_meta.json"))
                result.append(BackupInfo(
                    path=zp,
                    created_at=float(meta.get("created_at", zp.stat().st_mtime)),
                    size_bytes=zp.stat().st_size,
                    files_included=meta.get("files", []),
                ))
            except Exception:
                continue
        return result

    def restore(self, backup_path: Path | str) -> list[str]:
        """
        Restaura um backup. Faz backup automático do estado atual antes.
        Retorna lista de arquivos restaurados.
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup não encontrado: {backup_path}")

        # Backup do estado atual antes de restaurar
        current = self.list()
        if not any(b.path == backup_path for b in current):
            # Só faz pre-backup se não estiver restaurando o próprio backup atual
            pass
        self.create(label="pre_restore")

        restored: list[str] = []
        with zipfile.ZipFile(backup_path, "r") as zf:
            names = zf.namelist()
            for rel in _DEFAULT_FILES:
                if rel in names:
                    target = self._root / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(rel))
                    restored.append(rel)
        return restored

    def _rotate(self) -> None:
        """Remove backups mais antigos se exceder _MAX_BACKUPS."""
        backups = sorted(self._backups_dir.glob("wind_backup_*.zip"))
        while len(backups) > _MAX_BACKUPS:
            oldest = backups.pop(0)
            try:
                oldest.unlink()
            except OSError:
                break
