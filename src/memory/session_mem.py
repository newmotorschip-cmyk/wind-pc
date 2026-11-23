"""
Memória de sessão: histórico em memória da conversa atual.
Não persiste entre sessões — apenas durante a execução.
"""
from __future__ import annotations

from ..core.session import Message, Session


class SessionMemory:
    """Wrapper fino sobre Session para operações de memória de sessão."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_user(self, text: str) -> None:
        self._session.add("user", text)

    def add_assistant(self, text: str, model: str = "", cost_usd: float = 0.0) -> None:
        self._session.add("assistant", text, model=model, cost_usd=cost_usd)

    def get_history(self) -> list[dict]:
        return self._session.to_api_messages()

    def get_recent(self, n: int = 10) -> list[Message]:
        return self._session.last_n(n)

    def clear(self) -> None:
        self._session.messages.clear()

    def to_summary_text(self) -> str:
        lines = []
        for m in self._session.messages:
            prefix = "Felipe" if m.role == "user" else "WIND"
            lines.append(f"{prefix}: {m.content[:200]}")
        return "\n".join(lines)
