"""ProactiveMonitor — detecta situações que requerem atenção do Felipe."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class ProactiveAlert:
    type: str
    message: str
    severity: str = "info"  # info | warning | critical


class ProactiveMonitor:
    """Verifica projetos, casos, backups e retorna alertas proativos."""

    def __init__(
        self,
        db_path: str = "data/wind.db",
        backup_dir: str = "data/backups",
    ) -> None:
        self._db = Path(db_path)
        self._backup_dir = Path(backup_dir)

    # ── checks ─────────────────────────────────────────────────────────────────

    def check_projects(self, stale_days: int = 7) -> list[ProactiveAlert]:
        alerts: list[ProactiveAlert] = []
        if not self._db.exists():
            return alerts
        try:
            with sqlite3.connect(self._db) as conn:
                rows = conn.execute(
                    "SELECT name, updated_at FROM projects WHERE status='active'"
                ).fetchall()
        except sqlite3.OperationalError:
            return alerts
        cutoff = datetime.now() - timedelta(days=stale_days)
        for name, updated_at in rows:
            if not updated_at:
                continue
            try:
                dt = datetime.fromisoformat(updated_at)
            except ValueError:
                continue
            if dt < cutoff:
                days_ago = (datetime.now() - dt).days
                severity = "warning" if days_ago > 14 else "info"
                alerts.append(ProactiveAlert(
                    type="project_stale",
                    message=f"Projeto '{name}' sem atividade há {days_ago} dias.",
                    severity=severity,
                ))
        return alerts

    def check_cases(self, stale_days: int = 30) -> list[ProactiveAlert]:
        alerts: list[ProactiveAlert] = []
        if not self._db.exists():
            return alerts
        try:
            with sqlite3.connect(self._db) as conn:
                rows = conn.execute(
                    "SELECT vehicle_desc, created_at FROM service_cases WHERE status='open'"
                ).fetchall()
        except sqlite3.OperationalError:
            return alerts
        cutoff = datetime.now() - timedelta(days=stale_days)
        for vehicle, created_at in rows:
            if not created_at:
                continue
            try:
                dt = datetime.fromisoformat(created_at)
            except ValueError:
                continue
            if dt < cutoff:
                days_ago = (datetime.now() - dt).days
                alerts.append(ProactiveAlert(
                    type="case_stale",
                    message=f"Caso '{vehicle}' aberto há {days_ago} dias sem fechar.",
                    severity="warning",
                ))
        return alerts

    def check_backup(self, max_age_days: int = 7) -> list[ProactiveAlert]:
        if not self._backup_dir.exists():
            return [ProactiveAlert(
                type="backup_overdue",
                message="Pasta de backups não existe. Nenhum backup foi feito.",
                severity="warning",
            )]
        zips = sorted(self._backup_dir.glob("wind_backup_*.zip"), reverse=True)
        if not zips:
            return [ProactiveAlert(
                type="backup_overdue",
                message="Nenhum backup encontrado. Execute /backup.",
                severity="warning",
            )]
        latest_mtime = datetime.fromtimestamp(os.path.getmtime(zips[0]))
        age_days = (datetime.now() - latest_mtime).days
        if age_days >= max_age_days:
            severity = "critical" if age_days >= 14 else "warning"
            return [ProactiveAlert(
                type="backup_overdue",
                message=f"Último backup tem {age_days} dias. Execute /backup.",
                severity=severity,
            )]
        return []

    def check_budget(self, threshold: float = 0.8) -> list[ProactiveAlert]:
        # Sem acesso direto ao context manager — integração via injeção futura
        return []

    def check_all(self) -> list[ProactiveAlert]:
        alerts: list[ProactiveAlert] = []
        alerts.extend(self.check_projects())
        alerts.extend(self.check_cases())
        alerts.extend(self.check_backup())
        alerts.extend(self.check_budget())
        return alerts

    def format_alerts(self, alerts: list[ProactiveAlert]) -> str:
        if not alerts:
            return "✅ Nenhum alerta proativo."
        icons = {"info": "ℹ️ ", "warning": "⚠️ ", "critical": "🚨"}
        lines = [f"Alertas proativos ({len(alerts)}):"]
        for a in alerts:
            icon = icons.get(a.severity, "• ")
            lines.append(f"  {icon}[{a.type}] {a.message}")
        return "\n".join(lines)
