"""
Adaptador Claude Code para a WIND.
Dois modos:
  ClaudeCodeCLI    — usa o binário `claude` (Claude Code CLI) via subprocess.
  ClaudeCodeAdapter — fallback: API direta com system prompt focado em código.
  get_claude_code()  — retorna o melhor disponível.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


SYSTEM_TEMPLATE = """\
Você é a WIND — sócia técnica do Felipe (REPROTECH, Londrina/BR).
Neste momento está operando no modo de desenvolvimento de código.

Contexto do workspace:
{workspace_context}

Regras:
- Código Python 3.12+ por padrão. Use type hints e dataclasses onde cabível.
- Sem comentários óbvios. Apenas WHY quando não for evidente.
- Nunca exponha credenciais nem dados de classe SECRET.
- Respostas em português do Brasil, código em inglês.
"""

_CLAUDE_CLI_TIMEOUT = 120  # segundos


def _find_claude_binary() -> Optional[str]:
    """Localiza o binário `claude` no PATH ou em caminhos comuns."""
    candidate = shutil.which("claude")
    if candidate:
        return candidate
    # Caminhos extras no Windows (npm global, nvm)
    extra = [
        Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "claude",
        Path("/usr/local/bin/claude"),
    ]
    for p in extra:
        if p.exists():
            return str(p)
    return None


def _get_workspace_context(workspace_path: Optional[str] = None) -> str:
    lines: list[str] = []
    path = Path(workspace_path) if workspace_path else Path.cwd()
    lines.append(f"Diretório: {path}")
    py_files = list(path.glob("*.py"))[:10]
    if py_files:
        lines.append("Arquivos Python no raiz: " + ", ".join(f.name for f in py_files))
    if (path / "pyproject.toml").exists() or (path / "setup.py").exists():
        lines.append("Projeto Python detectado (pyproject.toml/setup.py)")
    if (path / "requirements.txt").exists():
        lines.append("requirements.txt presente")
    if (path / "src").is_dir():
        lines.append("Estrutura src/ detectada")
    return "\n".join(lines) if lines else "Workspace padrão"


class ClaudeCodeCLI:
    """
    Chama o Claude Code CLI (`claude`) via subprocess.
    Requer Node.js + npm install -g @anthropic-ai/claude-code.
    """

    def __init__(self, workspace_path: Optional[str] = None) -> None:
        self._binary = _find_claude_binary()
        self._workspace = workspace_path or os.getcwd()

    def is_available(self) -> bool:
        return self._binary is not None

    def name(self) -> str:
        return "claude_code_cli"

    @staticmethod
    def install_hint() -> str:
        return (
            "Para instalar o Claude Code CLI:\n"
            "  1. Instale Node.js: https://nodejs.org/\n"
            "  2. npm install -g @anthropic-ai/claude-code\n"
            "  3. Reinicie o terminal e execute: claude --version\n"
        )

    def run(self, prompt: str, cwd: Optional[str] = None) -> str:
        """
        Executa `claude -p <prompt>` no diretório do workspace.
        Retorna o stdout como string.
        """
        if not self._binary:
            raise RuntimeError(
                "Claude Code CLI não encontrado. " + self.install_hint()
            )
        work_dir = cwd or self._workspace
        try:
            result = subprocess.run(
                [self._binary, "-p", prompt],
                capture_output=True,
                text=True,
                cwd=work_dir,
                timeout=_CLAUDE_CLI_TIMEOUT,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                raise RuntimeError(f"claude CLI retornou código {result.returncode}: {stderr}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"claude CLI excedeu {_CLAUDE_CLI_TIMEOUT}s sem resposta.")

    def generate_code(self, prompt: str, language: str = "python") -> tuple[str, str, float]:
        text = self.run(f"[{language.upper()}] {prompt}")
        return text, self.name(), 0.0


class ClaudeCodeAdapter:
    """
    Fallback: API direta via ModelRouter com system prompt focado em código.
    Usado quando o Claude Code CLI não está instalado.
    """

    def __init__(self, router=None, workspace_path: Optional[str] = None) -> None:
        self._router = router
        self._workspace_path = workspace_path or os.getcwd()

    def is_available(self) -> bool:
        return self._router is not None

    def name(self) -> str:
        return "claude_code_api"

    def build_system_prompt(self, extra_context: str = "") -> str:
        ws_ctx = _get_workspace_context(self._workspace_path)
        if extra_context:
            ws_ctx = f"{ws_ctx}\n\n{extra_context}"
        return SYSTEM_TEMPLATE.format(workspace_context=ws_ctx)

    def call(
        self,
        messages: list[dict],
        task: str = "Gerar código",
        force_model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> tuple[str, str, float]:
        from src.router.models import TaskType

        if self._router is None:
            raise RuntimeError("ClaudeCodeAdapter requer router configurado.")

        system = self.build_system_prompt(f"Tarefa: {task}")
        return self._router.call(
            messages=messages,
            system=system,
            task_type=TaskType.CODING,
            max_tokens=max_tokens,
            force_model=force_model,
        )

    def generate_code(
        self,
        prompt: str,
        language: str = "python",
        force_model: Optional[str] = None,
    ) -> tuple[str, str, float]:
        messages = [{"role": "user", "content": f"[{language.upper()}] {prompt}"}]
        return self.call(messages, task=f"Gerar código {language}", force_model=force_model)


def get_claude_code(router=None, workspace_path: Optional[str] = None):
    """Retorna ClaudeCodeCLI se disponível, senão ClaudeCodeAdapter."""
    cli = ClaudeCodeCLI(workspace_path)
    if cli.is_available():
        return cli
    return ClaudeCodeAdapter(router=router, workspace_path=workspace_path)
