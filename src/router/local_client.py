"""
Stub para o modelo local (RTX 3080 via Ollama).
Substituir por implementação real quando Ollama estiver instalado.
"""
from .models import ModelSpec


class LocalClient:
    def call(
        self,
        messages: list[dict],
        system: str,
        model: ModelSpec,
        max_tokens: int = 2048,
    ) -> tuple[str, int, int]:
        raise NotImplementedError(
            "Modelo local não disponível ainda. "
            "Instale o Ollama e configure WIND_LOCAL_MODEL para habilitar."
        )
