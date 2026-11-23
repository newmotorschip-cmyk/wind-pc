"""
Memória episódica: registro de casos, interações e eventos com estado e confiança.
Persiste em SQLite via MemoryStore.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from .store import MemoryStore

MEM_TYPE = "episodic"


class EpisodicMemory:
    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def record_interaction(
        self,
        user_text: str,
        wind_text: str,
        session_id: str,
        model: str = "",
        tags: list[str] | None = None,
    ) -> str:
        return self._store.put(
            mem_type=MEM_TYPE,
            origin="session",
            content={"user": user_text, "wind": wind_text, "model": model},
            title=user_text[:80],
            tags=tags or [],
            confidence=1.0,
            state="validated",
            session_id=session_id,
        )

    def record_case(
        self,
        title: str,
        content: dict,
        tags: list[str] | None = None,
        confidence: float = 1.0,
        state: str = "hypothesis",
        session_id: str | None = None,
    ) -> str:
        """Registra um caso de serviço ou evento técnico."""
        return self._store.put(
            mem_type=MEM_TYPE,
            origin="user",
            content=content,
            title=title,
            tags=tags or [],
            confidence=confidence,
            state=state,
            session_id=session_id,
        )

    def search(self, query: str, limit: int = 5) -> list[dict]:
        return self._store.search(query, limit=limit, mem_type=MEM_TYPE)

    def get(self, item_id: str) -> Optional[dict]:
        item = self._store.get(item_id)
        if item and item["mem_type"] == MEM_TYPE:
            return item
        return None

    def recent(self, limit: int = 10) -> list[dict]:
        return self._store.list_by_type(MEM_TYPE, limit=limit)

    def validate(self, item_id: str) -> None:
        self._store.update_state(item_id, "validated")

    def mark_obsolete(self, item_id: str) -> None:
        self._store.update_state(item_id, "obsolete")
