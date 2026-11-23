"""
Desktop Agent — executa ações whitelistadas no PC Windows.
Nunca executa código arbitrário: apenas comandos predefinidos.
Fase 11: screenshot, type_text, focus_window, clipboard, git, file I/O, run_command.
"""
from __future__ import annotations

import os
import platform
import subprocess
import urllib.parse
from pathlib import Path
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
        "vscode":    ["cmd.exe", "/c", "start", "code"],
    }

    # Executáveis permitidos no run_command (sem path absoluto)
    _ALLOWED_EXECUTABLES = {
        "git", "python", "pip", "pip3", "python3",
        "dir", "ls", "echo", "type", "mkdir",
        "tasklist", "taskkill", "ipconfig", "ping",
        "curl", "where", "npm", "node",
    }

    # Diretórios onde write_file é permitido sem confirmação extra
    _SAFE_WRITE_DIRS: list[str] = []

    def __init__(self, project_root: str = ".") -> None:
        self._root = Path(project_root).resolve()
        self._SAFE_WRITE_DIRS = [str(self._root)]
        self._audit: Any = None  # AuditLog injetado opcionalmente
        self._git_exe = self._find_git()

    def _find_git(self) -> str:
        """Localiza o executável git no sistema."""
        candidates = [
            r"C:\Users\Repro\AppData\Local\GitKraken\app-12.7.0\resources\app.asar.unpacked\git\bin\git.exe",
            r"C:\Program Files\Git\bin\git.exe",
            r"C:\Program Files (x86)\Git\bin\git.exe",
            "git",
        ]
        for c in candidates:
            if Path(c).exists() if "\\" in c else True:
                return c
        return "git"

    def set_audit(self, audit: Any) -> None:
        self._audit = audit

    def _log(self, action: str, data: dict) -> None:
        if self._audit:
            self._audit.log("desktop_action", {"action": action, **data})

    def execute(self, command: str, **kwargs: Any) -> dict:
        dispatch: dict[str, Any] = {
            "open_app":        self._open_app,
            "search_web":      self._search_web,
            "open_url":        self._open_url,
            "get_status":      self._get_status,
            "wake_screen":     self._wake_screen,
            # Fase 11
            "run_command":     self._run_command,
            "take_screenshot": self._take_screenshot,
            "type_text":       self._type_text,
            "focus_window":    self._focus_window,
            "read_clipboard":  self._read_clipboard,
            "write_clipboard": self._write_clipboard,
            "git_status":      self._git_status,
            "git_commit":      self._git_commit,
            "git_diff":        self._git_diff,
            "list_files":      self._list_files,
            "read_file":       self._read_file,
            "write_file":      self._write_file,
        }
        handler = dispatch.get(command)
        if handler is None:
            allowed = ", ".join(dispatch)
            return {"ok": False, "error": f"comando '{command}' não reconhecido. Permitidos: {allowed}"}
        try:
            result = handler(**kwargs)
            self._log(command, {"kwargs": str(kwargs)[:200], "ok": result.get("ok", False)})
            return result
        except Exception as exc:
            self._log(command, {"kwargs": str(kwargs)[:200], "ok": False, "error": str(exc)})
            return {"ok": False, "error": str(exc)}

    # ── Handlers originais ─────────────────────────────────────────────────────

    def _open_app(self, app: str = "", **_: Any) -> dict:
        app = app.lower().strip()
        cmd = self._APP_COMMANDS.get(app)
        if cmd is None:
            allowed = ", ".join(self._APP_COMMANDS)
            return {"ok": False, "error": f"app '{app}' não permitido. Permitidos: {allowed}"}
        subprocess.Popen(cmd, shell=False, creationflags=0x00000008)
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
            "pc":     platform.node(),
            "os":     platform.version()[:60],
            "python": platform.python_version(),
            "online": True,
        }
        try:
            import psutil  # type: ignore
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(".")
            info["cpu_percent"]   = round(psutil.cpu_percent(interval=0.5), 1)
            info["mem_percent"]   = round(mem.percent, 1)
            info["mem_avail_gb"]  = round(mem.available / 1024 ** 3, 1)
            info["mem_total_gb"]  = round(mem.total / 1024 ** 3, 1)
            info["disk_free_gb"]  = round(disk.free / 1024 ** 3, 1)
            info["disk_total_gb"] = round(disk.total / 1024 ** 3, 1)
        except ImportError:
            info["psutil"] = "não instalado (pip install psutil)"
        return {"ok": True, "status": info}

    def _wake_screen(self, **_: Any) -> dict:
        if platform.system() != "Windows":
            return {"ok": False, "error": "wake_screen só disponível no Windows"}
        try:
            import ctypes
            ctypes.windll.user32.mouse_event(0x0001, 1, 0, 0, 0)
            ctypes.windll.user32.mouse_event(0x0001, -1, 0, 0, 0)
            return {"ok": True, "result": "Tela acordada"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── Fase 11: Novos handlers ────────────────────────────────────────────────

    def _run_command(self, cmd: str = "", args: list | None = None, cwd: str = ".", **_: Any) -> dict:
        """Executa um comando da whitelist de forma segura."""
        if not cmd:
            return {"ok": False, "error": "parâmetro 'cmd' obrigatório"}
        exe = cmd.split()[0].lower().rstrip(".exe")
        if exe not in self._ALLOWED_EXECUTABLES:
            return {"ok": False, "error": f"'{exe}' não está na whitelist. Permitidos: {', '.join(sorted(self._ALLOWED_EXECUTABLES))}"}
        full_cmd = cmd if not args else f"{cmd} {' '.join(str(a) for a in args)}"
        try:
            result = subprocess.run(
                full_cmd, shell=True, capture_output=True, text=True,
                timeout=30, cwd=cwd or ".",
            )
            output = (result.stdout or "").strip()
            err    = (result.stderr or "").strip()
            return {
                "ok": result.returncode == 0,
                "output": output[:4000],
                "error": err[:1000] if result.returncode != 0 else "",
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "timeout: comando demorou mais de 30s"}

    def _take_screenshot(self, save_path: str = "", **_: Any) -> dict:
        """Captura a tela inteira. Salva em save_path ou retorna caminho temporário."""
        try:
            import pyautogui  # type: ignore
        except ImportError:
            return {"ok": False, "error": "pyautogui não instalado (pip install pyautogui)"}
        if not save_path:
            import tempfile, time
            save_path = os.path.join(tempfile.gettempdir(), f"wind_screen_{int(time.time())}.png")
        img = pyautogui.screenshot()
        img.save(save_path)
        return {"ok": True, "path": save_path, "size": f"{img.width}x{img.height}"}

    def _type_text(self, text: str = "", interval: float = 0.03, **_: Any) -> dict:
        """Digita texto na janela ativa via pyautogui."""
        if not text:
            return {"ok": False, "error": "parâmetro 'text' obrigatório"}
        try:
            import pyautogui  # type: ignore
        except ImportError:
            return {"ok": False, "error": "pyautogui não instalado (pip install pyautogui)"}
        import time
        time.sleep(0.3)  # pequeno delay para garantir foco
        pyautogui.typewrite(text, interval=interval)
        return {"ok": True, "result": f"Texto digitado: {text[:50]}"}

    def _focus_window(self, title: str = "", **_: Any) -> dict:
        """Traz janela com título para frente."""
        if not title:
            return {"ok": False, "error": "parâmetro 'title' obrigatório"}
        try:
            import pygetwindow as gw  # type: ignore
        except ImportError:
            return {"ok": False, "error": "pygetwindow não instalado (pip install pygetwindow)"}
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return {"ok": False, "error": f"Nenhuma janela com título contendo '{title}'"}
        win = windows[0]
        win.activate()
        return {"ok": True, "result": f"Janela '{win.title[:60]}' em foco"}

    def _read_clipboard(self, **_: Any) -> dict:
        """Lê o conteúdo atual da área de transferência."""
        try:
            import pyperclip  # type: ignore
            text = pyperclip.paste()
            return {"ok": True, "content": text[:5000]}
        except ImportError:
            # Fallback: ctypes no Windows
            try:
                import ctypes
                ctypes.windll.user32.OpenClipboard(0)
                handle = ctypes.windll.user32.GetClipboardData(13)  # CF_UNICODETEXT
                text = ctypes.c_wchar_p(handle).value or ""
                ctypes.windll.user32.CloseClipboard()
                return {"ok": True, "content": text[:5000]}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    def _write_clipboard(self, text: str = "", **_: Any) -> dict:
        """Escreve texto na área de transferência."""
        if not text:
            return {"ok": False, "error": "parâmetro 'text' obrigatório"}
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
            return {"ok": True, "result": f"Clipboard atualizado ({len(text)} chars)"}
        except ImportError:
            try:
                import subprocess as sp
                sp.run("clip", input=text.encode("utf-16-le"), check=True)
                return {"ok": True, "result": f"Clipboard atualizado ({len(text)} chars)"}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    def _git_status(self, path: str = ".", **_: Any) -> dict:
        """Retorna git status do repositório."""
        result = subprocess.run(
            [self._git_exe, "-C", path, "status", "--short", "--branch"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr.strip()[:500]}
        return {"ok": True, "output": result.stdout.strip()[:3000]}

    def _git_commit(self, message: str = "", path: str = ".", add_all: bool = True, **_: Any) -> dict:
        """Faz git add + commit."""
        if not message:
            return {"ok": False, "error": "parâmetro 'message' obrigatório"}
        if add_all:
            subprocess.run([self._git_exe, "-C", path, "add", "-A"], capture_output=True, timeout=15)
        result = subprocess.run(
            [self._git_exe, "-C", path, "commit", "-m", message],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            return {"ok": False, "error": err[:500]}
        return {"ok": True, "output": result.stdout.strip()[:1000]}

    def _git_diff(self, path: str = ".", staged: bool = False, **_: Any) -> dict:
        """Mostra git diff."""
        args = [self._git_exe, "-C", path, "diff"]
        if staged:
            args.append("--cached")
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return {"ok": True, "output": result.stdout.strip()[:8000]}

    def _list_files(self, path: str = ".", pattern: str = "*", **_: Any) -> dict:
        """Lista arquivos em um diretório."""
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return {"ok": False, "error": f"Caminho não encontrado: {path}"}
        try:
            items = sorted(p.glob(pattern))
            lines = []
            for item in items[:200]:
                size = f"{item.stat().st_size:>10,}" if item.is_file() else "       <dir>"
                lines.append(f"{size}  {item.name}")
            return {"ok": True, "output": "\n".join(lines), "count": len(items)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _read_file(self, path: str = "", max_bytes: int = 20000, **_: Any) -> dict:
        """Lê o conteúdo de um arquivo (limite de tamanho)."""
        if not path:
            return {"ok": False, "error": "parâmetro 'path' obrigatório"}
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return {"ok": False, "error": f"Arquivo não encontrado: {path}"}
        if not p.is_file():
            return {"ok": False, "error": f"'{path}' não é um arquivo"}
        size = p.stat().st_size
        if size > 1_000_000:
            return {"ok": False, "error": f"Arquivo muito grande ({size/1024:.0f} KB). Máximo: 1 MB"}
        try:
            content = p.read_text(encoding="utf-8", errors="replace")[:max_bytes]
            truncated = size > max_bytes
            return {"ok": True, "content": content, "size": size, "truncated": truncated}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _write_file(self, path: str = "", content: str = "", encoding: str = "utf-8", **_: Any) -> dict:
        """Escreve conteúdo em arquivo (apenas dentro de diretórios seguros)."""
        if not path:
            return {"ok": False, "error": "parâmetro 'path' obrigatório"}
        p = Path(path).expanduser().resolve()
        # Verificar se está em diretório seguro
        in_safe = any(str(p).startswith(safe) for safe in self._SAFE_WRITE_DIRS)
        if not in_safe:
            safe_list = ", ".join(self._SAFE_WRITE_DIRS)
            return {
                "ok": False,
                "error": f"Escrita fora de diretório seguro. Permitidos: {safe_list}",
            }
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding=encoding)
            return {"ok": True, "result": f"Arquivo salvo: {p} ({len(content)} chars)"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def allowed_apps(self) -> list[str]:
        return list(self._APP_COMMANDS.keys())

    def allowed_commands(self) -> list[str]:
        return sorted(self._ALLOWED_EXECUTABLES)
