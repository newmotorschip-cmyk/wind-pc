"""
Log de auditoria append-only da WIND.
Cada evento é uma linha JSONL em data/audit.jsonl.
Nunca deleta, nunca reescreve — apenas acrescenta.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

AUDIT_PATH = Path(os.getenv("WIND_AUDIT_PATH", "data/audit.jsonl"))


class AuditLog:
    def __init__(self, path: Path = AUDIT_PATH) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event: str,
        data: dict,
        session_id: str = "",
        level: str = "info",
    ) -> None:
        record = {
            "ts": time.time(),
            "level": level,
            "event": event,
            "session": session_id,
            **data,
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_call(
        self,
        session_id: str,
        model: str,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        data_class: str = "public",
    ) -> None:
        self.log(
            "model_call",
            {
                "model": model,
                "task_type": task_type,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost_usd, 6),
                "data_class": data_class,
            },
            session_id=session_id,
        )

    def log_guardian_block(self, session_id: str, reason: str) -> None:
        self.log(
            "guardian_block",
            {"reason": reason},
            session_id=session_id,
            level="warn",
        )

    def tail(self, n: int = 20) -> list[dict]:
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(l) for l in lines[-n:]]
