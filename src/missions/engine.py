"""
Motor de execução de missões da WIND.
Executa passos em sequência, salva checkpoints, suporta pausa e retomada.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from .mission import Mission, MissionStatus, MissionStep, MissionType, StepStatus
from .queue import MissionQueue


ToolFn = Callable[[MissionStep, dict], dict]


class MissionEngine:
    def __init__(self, queue: MissionQueue, session_id: str = "") -> None:
        self._queue = queue
        self._session_id = session_id
        self._tools: dict[str, ToolFn] = {}

    def register_tool(self, name: str, fn: ToolFn) -> None:
        """Registra uma ferramenta que os passos podem chamar."""
        self._tools[name] = fn

    def create(
        self,
        title: str,
        steps: list[dict],
        mission_type: MissionType = MissionType.GENERIC,
        project_id: str | None = None,
        context: dict | None = None,
    ) -> Mission:
        """Cria e persiste uma nova missão."""
        plan = [
            MissionStep(
                description=s.get("description", ""),
                tool=s.get("tool", "wind_chat"),
                input=s.get("input", {}),
            )
            for s in steps
        ]
        mission = Mission(
            title=title,
            mission_type=mission_type,
            project_id=project_id,
            plan=plan,
            context=context or {},
            session_id=self._session_id,
        )
        self._queue.save(mission)
        return mission

    def run(
        self,
        mission: Mission,
        on_step_done: Optional[Callable[[MissionStep], None]] = None,
    ) -> Mission:
        """
        Executa a missão passo a passo a partir do current_step.
        Salva checkpoint após cada passo.
        """
        mission.status = MissionStatus.RUNNING
        mission.session_id = self._session_id
        self._queue.save(mission)

        while mission.current_step < len(mission.plan):
            step = mission.plan[mission.current_step]
            if step.status == StepStatus.COMPLETED:
                mission.current_step += 1
                continue

            step.status = StepStatus.RUNNING
            step.started_at = time.time()
            self._queue.save(mission)

            try:
                tool_fn = self._tools.get(step.tool)
                if tool_fn is None:
                    raise NotImplementedError(f"Ferramenta '{step.tool}' não registrada.")
                result = tool_fn(step, mission.context)
                step.output = result
                mission.context.update(result.get("context_update", {}))
                step.status = StepStatus.COMPLETED
                step.completed_at = time.time()
            except Exception as exc:
                step.status = StepStatus.FAILED
                step.error = str(exc)
                step.completed_at = time.time()
                mission.status = MissionStatus.FAILED
                self._queue.save(mission)
                if on_step_done:
                    on_step_done(step)
                return mission

            mission.current_step += 1
            self._queue.save(mission)

            if on_step_done:
                on_step_done(step)

        mission.status = MissionStatus.COMPLETED
        self._queue.save(mission)
        return mission

    def pause(self, mission: Mission) -> Mission:
        mission.status = MissionStatus.PAUSED
        self._queue.save(mission)
        return mission

    def cancel(self, mission: Mission) -> Mission:
        mission.status = MissionStatus.CANCELLED
        self._queue.save(mission)
        return mission

    def resume(self, mission_id: str) -> Optional[Mission]:
        """Retoma uma missão pausada pelo ID."""
        mission = self._queue.get(mission_id)
        if mission and mission.status == MissionStatus.PAUSED:
            return self.run(mission)
        return mission
