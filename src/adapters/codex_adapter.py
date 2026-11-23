"""
Adaptador Codex (OpenAI o4-mini) para a WIND.
Usado para geração de código pesada que se beneficia do raciocínio estendido do o4-mini.
"""
from __future__ import annotations

from typing import Optional


SYSTEM_PROMPT = """\
Você é o módulo de geração de código da WIND — IA técnica do Felipe (REPROTECH).
Use raciocínio estendido para produzir código correto, testável e idiomático.
Responda sempre em português do Brasil (comentários/explicações), código em inglês.
Nunca inclua credenciais, tokens ou dados sensíveis no código gerado.
"""


class CodexAdapter:
    """
    Adaptador direto para o OpenAI o4-mini via OpenAIClient.
    Especializado em geração de código com raciocínio (chain-of-thought implícito do o4-mini).
    """

    MODEL = "o4-mini"

    def __init__(self, openai_client=None) -> None:
        self._client = openai_client

    def _get_client(self):
        if self._client is not None:
            return self._client
        from src.router.openai_client import OpenAIClient
        return OpenAIClient()

    def generate(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 8192,
    ) -> tuple[str, int, int]:
        """
        Gera código via o4-mini.
        Retorna (text, input_tokens, output_tokens).
        """
        client = self._get_client()
        system = SYSTEM_PROMPT
        if context:
            system = f"{SYSTEM_PROMPT}\nContexto adicional:\n{context}"

        messages = [{"role": "user", "content": prompt}]
        return client.call(
            messages=messages,
            system=system,
            model=self.MODEL,
            max_tokens=max_tokens,
        )

    def refactor(self, code: str, instructions: str, max_tokens: int = 4096) -> tuple[str, int, int]:
        """Refatora código existente seguindo instruções."""
        prompt = f"Refatore o seguinte código seguindo as instruções:\n\nInstruções: {instructions}\n\n```\n{code}\n```"
        return self.generate(prompt, max_tokens=max_tokens)

    def explain(self, code: str, max_tokens: int = 2048) -> tuple[str, int, int]:
        """Explica o que um trecho de código faz."""
        prompt = f"Explique em português do Brasil o que este código faz:\n\n```\n{code}\n```"
        return self.generate(prompt, max_tokens=max_tokens)
