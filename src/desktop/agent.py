"""
Desktop Agent — executa ações whitelistadas no PC Windows.
Nunca executa código arbitrário: apenas comandos predefinidos.
"""
from __future__ import annotations

import os
import platform
import subprocess
import urllib.parse
from typing import Any


class DesktopAgent:
    """Executa ações de desktop Windows de forma segura (apenas whitelist)."""

    # Apps permitidos → comando a executar numa nova janela
    _APP_COMMANDS: dict[str, list[str]] = {
        "claude":    ["cmd.exe", "/c", "start", "cmd.exe", "/k", "claude"],
        "codex":     ["cmd.exe", "/c", "start", "cmd.exe", "/k", "codex"],
        "terminal":  ["cmd.exe", "/c", "start", "cmd.exe"],
        "explorer":  ["cmd.exe", "/c", "start", "explorer.exe"],
        "notepad":   ["cmd.exe", "/c", "start", "notepad.exe"],
        "browser":   ["cmd.exe", "/c", "start", ""],
    }

    def execute(self, command: str, **kwargs: Any) -> dict:
        """
        Despacha um comando de desktop.
        Retorna {"ok": True, "result": "..."} ou {"ok": False, "error": "..."}.
        """
        dispatch: dict[str, Any] = {
            "open_app":    self._open_app,
            "search_web":  self._search_web,
            "open_url":    self._open_url,
            "get_status":  self._get_status,
            "wake_screen": self._wake_screen,
        }
        handler = dispatch.get(command)
        if handler is None:
            allowed = ", ".join(dispatch)
            return {"ok": False, "error": f"comando '{command}' não reconhecido. Permitidos: {allowed}"}
        try:
            return handler(**kwargs)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── Handlers ───────────────────────────────────────────────────────────────

    def _open_app(self, app: str = "", **_: Any) -> dict:
        app = app.lower().strip()
        cmd = self._APP_COMMANDS.get(app)
        if cmd is None:
            allowed = ", ".join(self._APP_COMMANDS)
            return {"ok": False, "error": f"app '{app}' não permitido. Permitidos: {allowed}"}
        subprocess.Popen(cmd, shell=False, creationflags=0x00000008)  # DETACHED_PROCESS
        return {"ok": True, "result": f"{app.capitalize()} sendo aberto..."}

    def _search_web(self, query: str = "", **_: Any) -> dict:
        if not query.strip():
            return {"ok": False, "error": "parâmetro 'query' obrigatório"}
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query.strip())
        return self._open_url(url=url)

    def _open_url(self, url: str = "", **_: Any) -> dict:
        if not url:
            return {"ok": False, "error": "parâmetro 'url' obrigatório"}
        if not url.startswith(("http://", "https://")):
            return {"ok": False, "error": "apenas URLs http:// ou https:// são permitidas"}
        cmd = ["cmd.exe", "/c", "start", "", url]
        subprocess.Popen(cmd, shell=False)
        return {"ok": True, "result": f"Abrindo {url[:70]}..."}

    def _get_status(self, **_: Any) -> dict:
        info: dict[str, Any] = {
            "pc":       platform.node(),
            "os":       platform.version()[:60],
            "python":   platform.python_version(),
            "online":   True,
        }
        try:
            import psutil  # type: ignore
            mem = psutil.virtual_memory()
            info["cpu_percent"]  = round(psutil.cpu_percent(interval=0.5), 1)
            info["mem_percent"]  = round(mem.percent, 1)
            info["mem_avail_gb"] = round(mem.available / 1024 ** 3, 1)
            info["mem_total_gb"] = round(mem.total / 1024 ** 3, 1)
        except ImportError:
            info["psutil"] = "não instalado (pip install psutil para dados de CPU/RAM)"
        return {"ok": True, "status": info}

    def _wake_screen(self, **_: Any) -> dict:
        """Move o mouse 1 pixel para evitar proteção de tela / bloqueio."""
        if platform.system() != "Windows":
            return {"ok": False, "error": "wake_screen só disponível no Windows"}
        try:
            import ctypes
            ctypes.windll.user32.mouse_event(0x0001, 1, 0, 0, 0)  # MOUSEEVENTF_MOVE
            ctypes.windll.user32.mouse_event(0x0001, -1, 0, 0, 0)
            return {"ok": True, "result": "Tela acordada"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def allowed_apps(self) -> list[str]:
        return list(self._APP_COMMANDS.keys())
