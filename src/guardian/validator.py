"""
Validador pré-chamada do Guardian.
Verifica se é seguro enviar o conteúdo para um modelo remoto.
"""
from __future__ import annotations

from .classifier import DataClass, classify_batch


class ValidationError(Exception):
    """Levantado quando o Guardian bloqueia uma chamada."""


class GuardianValidator:
    def validate_remote_call(
        self,
        messages: list[dict],
        system: str,
        provider: str,
        purpose: str = "",
    ) -> None:
        """
        Verifica se é seguro enviar as mensagens para um modelo remoto.
        Levanta ValidationError se detectar dados proibidos.
        """
        if provider == "local":
            return  # modelo local nunca precisa de validação de envio remoto

        all_texts  = [system] + [m.get("content", "") for m in messages]
        # SECRET e FINANCIAL: verificar tudo (system prompt nunca deve ter segredos)
        all_class  = classify_batch(all_texts)

        if all_class == DataClass.SECRET:
            raise ValidationError(
                "GUARDIAN BLOQUEOU: dados de classe SECRET detectados. "
                "Nunca envie segredos (chaves de API, senhas, tokens) para modelos remotos."
            )

        if all_class == DataClass.FINANCIAL:
            raise ValidationError(
                "GUARDIAN BLOQUEOU: dados financeiros (CPF, CNPJ, conta, PIX) detectados. "
                "Dados financeiros não saem do PC sem regra explícita aprovada pelo Felipe."
            )

        # PERSONAL e CONFIDENTIAL_CLIENT: verificar apenas mensagens do usuário
        # (o system prompt é texto do sistema, não dados de cliente)
        msg_texts = [m.get("content", "") for m in messages if m.get("role") == "user"]
        if msg_texts:
            msg_class = classify_batch(msg_texts)
            if msg_class in (DataClass.PERSONAL, DataClass.CONFIDENTIAL_CLIENT):
                import sys
                print(
                    f"[GUARDIAN AVISO] Dados {msg_class.value} detectados na mensagem. "
                    "Certifique-se de remover identificadores antes de enviar para modelos remotos.",
                    file=sys.stderr,
                )

    def classify_input(self, text: str) -> str:
        from .classifier import classify
        return classify(text).value
