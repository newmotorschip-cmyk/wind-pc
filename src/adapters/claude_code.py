"""
Adaptador Claude Code para a WIND.
Fornece prompts especializados para geração e revisão de código,
com contexto de workspace injetado.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


SYSTEM_TEMPLATE = """\
Você é a WIND — sócia técnica do Felipe (REPROTECH, Londrina/PR).
Neste momento está operando no modo de desenvolvimento de código.

Contexto do workspace:
{workspace_context}

Regras:
- Código Python 3.12+ por padrão. Use type hints e dataclasses onde cabível.
- Sem comentários óbvios. Apenas WHY quando não for evidente.
- Nunca exponha credenciais nem dados de classe SECRET.
- Respostas em português do Brasil, código em inglês.
"""


def _get_workspace_context(workspace_path: Optional[str] = None) -> str:
    """Coleta contexto básico do workspace (sem ler arquivos sensíveis)."""
    lines: list[str] = []

    path = Path(workspace_path) if workspace_path else Path.cwd()
    lines.append(f"Diretório: {path}")

    # Lista arquivos Python na raiz (sem recursão profunda)
    py_files = list(path.glob("*.py"))[:10]
    if py_files:
        lines.append("Arquivos Python no raiz: " + ", ".join(f.name for f in py_files))

    # Detecta framework/projeto
    if (path / "pyproject.toml").exists() or (path / "setup.py").exists():
        lines.append("Projeto Python detectado (pyproject.toml/setup.py)")
    if (path / "requirements.txt").exists():
        lines.append("requirements.txt presente")
    if (path / "src").is_dir():
        lines.append("Estrutura src/ detectada")

    return "\n".join(lines) if lines else "Workspace padrão"


class ClaudeCodeAdapter:
    """
    Adaptador de alto nível para tarefas de desenvolvimento.
    Injeta contexto de workspace no system prompt antes de chamar o router.
    """

    def __init__(self, router=None, workspace_path: Optional[str] = None) -> None:
        self._router = router
        self._workspace_path = workspace_path or os.getcwd()

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
        """
        Chama o router com contexto de código.
        Retorna (text, model_id, cost_usd).
        """
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
        """Atalho para geração de código."""
        messages = [{"role": "user", "content": f"[{language.upper()}] {prompt}"}]
        return self.call(messages, task=f"Gerar código {language}", force_model=force_model)
