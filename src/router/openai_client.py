"""
Wrapper do SDK OpenAI para a WIND.
Usado principalmente para tarefas de codificação intensiva (Codex).
Requer OPENAI_API_KEY no ambiente.
"""
from __future__ import annotations

import os
from typing import Optional

import openai

from .models import ModelSpec


class OpenAIClient:
    def __init__(self) -> None:
        self._client: Optional[openai.OpenAI] = None

    def _get_client(self) -> openai.OpenAI:
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise EnvironmentError(
                    "OPENAI_API_KEY não configurada. "
                    "Defina: setx OPENAI_API_KEY sk-..."
                )
            self._client = openai.OpenAI(api_key=api_key)
        return self._client

    def call(
        self,
        messages: list[dict],
        system: str,
        model: ModelSpec,
        max_tokens: int = 2048,
    ) -> tuple[str, int, int]:
        """
        Chama a API OpenAI via chat.completions.
        Retorna (texto, input_tokens, output_tokens).
        """
        client = self._get_client()
        full_messages = [{"role": "system", "content": system}, *messages]
        response = client.chat.completions.create(
            model=model.id,
            messages=full_messages,
            max_completion_tokens=max_tokens,
        )
        text = response.choices[0].message.content or ""
        input_tok = response.usage.prompt_tokens if response.usage else 0
        output_tok = response.usage.completion_tokens if response.usage else 0
        return text, input_tok, output_tok
