import os
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    TRIAGE = "triage"           # classificação, extração, triagem rápida
    CONVERSATION = "conversation"  # conversa geral
    REASONING = "reasoning"      # análise, diagnóstico, raciocínio
    HARD = "hard"                # raciocínio difícil, múltiplos passos
    CODING = "coding"            # geração intensiva de código


class ModelTier(Enum):
    LOCAL = "local"       # RTX 3080 (futuro Ollama)
    FAST = "fast"         # Haiku — triagem e conversa simples
    STANDARD = "standard" # Sonnet — raciocínio padrão
    HEAVY = "heavy"       # Opus — casos difíceis
    CODE = "code"         # Codex — código intensivo


@dataclass
class ModelSpec:
    id: str
    tier: ModelTier
    cost_per_1k_input: float
    cost_per_1k_output: float
    context_window: int
    provider: str

    def available(self) -> bool:
        if self.provider == "anthropic":
            return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
        if self.provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
        if self.provider == "local":
            return False  # Ollama não instalado ainda
        return False

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.cost_per_1k_input + output_tokens * self.cost_per_1k_output) / 1000


MODELS: dict[str, ModelSpec] = {
    "local-stub": ModelSpec(
        id="local-stub",
        tier=ModelTier.LOCAL,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        context_window=4096,
        provider="local",
    ),
    "claude-haiku-5-5": ModelSpec(
        id="claude-haiku-5-5",
        tier=ModelTier.FAST,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        context_window=200000,
        provider="anthropic",
    ),
    "claude-sonnet-5-5": ModelSpec(
        id="claude-sonnet-5-5",
        tier=ModelTier.STANDARD,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        context_window=200000,
        provider="anthropic",
    ),
    "claude-opus-5-5": ModelSpec(
        id="claude-opus-5-5",
        tier=ModelTier.HEAVY,
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        context_window=200000,
        provider="anthropic",
    ),
    "o4-mini": ModelSpec(
        id="o4-mini",
        tier=ModelTier.CODE,
        cost_per_1k_input=0.0015,
        cost_per_1k_output=0.006,
        context_window=200000,
        provider="openai",
    ),
}

# Tabela de roteamento: task_type -> lista ordenada de modelos a tentar
ROUTING: dict[TaskType, list[str]] = {
    TaskType.TRIAGE:       ["local-stub", "claude-haiku-5-5", "claude-sonnet-5-5"],
    TaskType.CONVERSATION: ["claude-haiku-5-5", "claude-sonnet-5-5"],
    TaskType.REASONING:    ["claude-sonnet-5-5", "claude-opus-5-5"],
    TaskType.HARD:         ["claude-opus-5-5", "claude-sonnet-5-5"],
    TaskType.CODING:       ["o4-mini", "claude-sonnet-5-5"],
}
