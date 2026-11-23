"""
Roteador de modelos da WIND.
Escolhe o melhor modelo disponível para cada tipo de tarefa,
respeitando o orçamento e a disponibilidade de chaves de API.
"""
from __future__ import annotations

from typing import Optional

from ..core.context import ContextManager
from .models import MODELS, ROUTING, ModelSpec, TaskType
from .claude_client import ClaudeClient
from .openai_client import OpenAIClient
from .local_client import LocalClient


class ModelRouter:
    def __init__(self, ctx: ContextManager) -> None:
        self.ctx = ctx
        self._claude = ClaudeClient()
        self._openai = OpenAIClient()
        self._local = LocalClient()

    def _pick_model(self, task_type: TaskType, estimated_tokens: int = 500) -> ModelSpec:
        """Retorna o primeiro modelo disponível e dentro do orçamento para o task_type."""
        candidates = ROUTING.get(task_type, ["claude-sonnet-5-5"])
        for model_id in candidates:
            spec = MODELS[model_id]
            if not spec.available():
                continue
            est_cost = spec.estimate_cost(estimated_tokens, estimated_tokens)
            if self.ctx.can_spend(est_cost):
                return spec
        raise RuntimeError(
            f"Nenhum modelo disponível para '{task_type.value}'. "
            f"Verifique as chaves de API e o orçamento (restante: US$ {self.ctx.remaining:.4f})."
        )

    def call(
        self,
        messages: list[dict],
        system: str,
        task_type: TaskType = TaskType.CONVERSATION,
        max_tokens: int = 2048,
        force_model: Optional[str] = None,
    ) -> tuple[str, str, float]:
        """
        Chama o modelo adequado.
        Retorna (resposta_texto, model_id_usado, custo_usd).
        """
        if force_model:
            model = MODELS[force_model]
        else:
            model = self._pick_model(task_type)

        if model.provider == "anthropic":
            text, inp, out = self._claude.call(messages, system, model, max_tokens)
        elif model.provider == "openai":
            text, inp, out = self._openai.call(messages, system, model, max_tokens)
        elif model.provider == "local":
            text, inp, out = self._local.call(messages, system, model, max_tokens)
        else:
            raise ValueError(f"Provider desconhecido: {model.provider}")

        cost = model.estimate_cost(inp, out)
        self.ctx.record(model.id, inp, out, cost, task_type.value)
        return text, model.id, cost

    def status(self) -> dict:
        available = {k: v.available() for k, v in MODELS.items()}
        return {
            "models_available": {k: v for k, v in available.items() if v},
            "models_unavailable": {k: v for k, v in available.items() if not v},
            "budget": self.ctx.summary(),
        }
