"""
Dataclasses para o motor de missões da WIND.
Uma missão é uma sequência durável de passos com checkpoint e retomada.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MissionStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    PAUSED    = "paused"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    SKIPPED   = "skipped"


class MissionType(str, Enum):
    PROJECT_CONTINUATION = "project_continuation"
    CODE_GENERATION      = "code_generation"
    ANALYSIS             = "analysis"
    RESEARCH             = "research"
    GENERIC              = "generic"


@dataclass
class MissionStep:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    tool: str = "wind_chat"      # wind_chat | generate_code | read_file | write_file | remember
    input: dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    output: dict[str, Any] | None = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "tool": self.tool,
            "input": self.input,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MissionStep":
        d = dict(d)
        d["status"] = StepStatus(d.get("status", "pending"))
        return cls(**d)


@dataclass
class Mission:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mission_type: MissionType = MissionType.GENERIC
    status: MissionStatus = MissionStatus.PENDING
    project_id: str | None = None
    plan: list[MissionStep] = field(default_factory=list)
    current_step: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def is_done(self) -> bool:
        return self.status in (MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED)

    @property
    def progress(self) -> str:
        total = len(self.plan)
        done = sum(1 for s in self.plan if s.status == StepStatus.COMPLETED)
        return f"{done}/{total}"

    def current(self) -> MissionStep | None:
        if self.current_step < len(self.plan):
            return self.plan[self.current_step]
        return None

    def summary(self) -> str:
        lines = [f"Missão: {self.title} [{self.status.value}] {self.progress}"]
        for i, step in enumerate(self.plan):
            marker = "→" if i == self.current_step else ("✓" if step.status == StepStatus.COMPLETED else "·")
            lines.append(f"  {marker} [{i+1}] {step.description}")
        return "\n".join(lines)
