"""
Memória semântica: conhecimento técnico pesquisável por texto completo (FTS5).
Usada para guardar fatos técnicos, procedimentos validados e conhecimento do domínio.
"""
from __future__ import annotations

from typing import Optional

from .store import MemoryStore

MEM_TYPE = "semantic"


class SemanticMemory:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def store_knowledge(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        confidence: float = 1.0,
        state: str = "proposed",
        origin: str = "wind",
    ) -> str:
        """
        Armazena um item de conhecimento técnico.
        state='proposed' até ser validado pelo Felipe ou por teste objetivo.
        """
        return self._store.put(
            mem_type=MEM_TYPE,
            origin=origin,
            content=content,
            title=title,
            tags=tags or [],
            confidence=confidence,
            state=state,
        )

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Busca por texto completo."""
        return self._store.search(query, limit=limit, mem_type=MEM_TYPE)

    def get(self, item_id: str) -> Optional[dict]:
        item = self._store.get(item_id)
        if item and item["mem_type"] == MEM_TYPE:
            return item
        return None

    def validate(self, item_id: str) -> None:
        """Marca como validado — requer aprovação do Felipe ou teste objetivo."""
        self._store.update_state(item_id, "validated")

    def mark_obsolete(self, item_id: str) -> None:
        self._store.update_state(item_id, "obsolete")

    def recent(self, limit: int = 20) -> list[dict]:
        return self._store.list_by_type(MEM_TYPE, limit=limit)

    def format_results(self, results: list[dict]) -> str:
        """Formata resultados de busca para inclusão no contexto do modelo."""
        if not results:
            return ""
        lines = ["[Memória semântica relevante]"]
        for r in results:
            state_tag = f"[{r['state']}]" if r["state"] != "validated" else ""
            lines.append(f"- {r['title']} {state_tag}: {r['content'][:300]}")
        return "\n".join(lines)
