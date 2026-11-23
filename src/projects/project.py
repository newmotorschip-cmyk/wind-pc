"""
ProjectCard — card de projeto persistido da WIND.
Marco da Fase 2: "continue projeto X" funciona entre sessões.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProjectStatus(str, Enum):
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"
    ARCHIVED  = "archived"


@dataclass
class ProjectCard:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    tags: list[str] = field(default_factory=list)
    next_action: str = ""
    decisions: list[dict[str, Any]] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_decision(self, decision: str, context: str = "") -> None:
        self.decisions.append({
            "text": decision,
            "context": context,
            "at": time.time(),
        })
        self.updated_at = time.time()

    def summary(self) -> str:
        lines = [
            f"Projeto: {self.name} [{self.status.value}]",
            f"  Descrição: {self.description}" if self.description else "",
            f"  Próximo passo: {self.next_action}" if self.next_action else "",
            f"  Decisões: {len(self.decisions)}",
            f"  Tags: {', '.join(self.tags)}" if self.tags else "",
        ]
        return "\n".join(l for l in lines if l)
