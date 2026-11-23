"""
Wrapper do SDK Anthropic para a WIND.
Requer ANTHROPIC_API_KEY ou ANTHROPIC_AUTH_TOKEN no ambiente.
"""
from __future__ import annotations

import os
from typing import Optional

import anthropic

from .models import ModelSpec


class ClaudeClient:
    def __init__(self) -> None:
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
            if not api_key and not auth_token:
                raise EnvironmentError(
                    "ANTHROPIC_API_KEY não configurada. "
                    "Obtenha em console.anthropic.com e defina: "
                    "setx ANTHROPIC_API_KEY sk-ant-..."
                )
            self._client = anthropic.Anthropic(
                api_key=api_key,
                auth_token=auth_token if not api_key else None,
            )
        return self._client

    def call(
        self,
        messages: list[dict],
        system: str,
        model: ModelSpec,
        max_tokens: int = 2048,
    ) -> tuple[str, int, int]:
        """
        Chama a API do Claude.
        Retorna (texto, input_tokens, output_tokens).
        """
        client = self._get_client()
        response = client.messages.create(
            model=model.id,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        text = text_blocks[0] if text_blocks else ""
        input_tok = response.usage.input_tokens
        output_tok = response.usage.output_tokens
        return text, input_tok, output_tok
