"""
Testes unitários — Motor de Missões (Fase 2).
"""
import json
import tempfile
from pathlib import Path

import pytest

from src.missions.mission import Mission, MissionStatus, MissionStep, MissionType, StepStatus
from src.missions.queue import MissionQueue
from src.missions.engine import MissionEngine


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_missions.db"


@pytest.fixture
def queue(tmp_db):
    return MissionQueue(tmp_db)


@pytest.fixture
def engine(queue):
    return MissionEngine(queue, session_id="test-session")


# ── MissionStep ────────────────────────────────────────────────────────────────

class TestMissionStep:
    def test_to_dict_round_trip(self):
        step = MissionStep(description="Fazer algo", tool="wind_chat")
        d = step.to_dict()
        restored = MissionStep.from_dict(d)
        assert restored.description == step.description
        assert restored.tool == step.tool
        assert restored.status == StepStatus.PENDING

    def test_default_status_pending(self):
        step = MissionStep()
        assert step.status == StepStatus.PENDING


# ── Mission ────────────────────────────────────────────────────────────────────

class TestMission:
    def test_progress_empty(self):
        m = Mission(title="Teste")
        assert m.progress == "0/0"

    def test_progress_partial(self):
        s1 = MissionStep(status=StepStatus.COMPLETED)
        s2 = MissionStep(status=StepStatus.PENDING)
        m = Mission(title="Teste", plan=[s1, s2])
        assert m.progress == "1/2"

    def test_is_done_running(self):
        m = Mission(title="Teste", status=MissionStatus.RUNNING)
        assert not m.is_done

    def test_is_done_completed(self):
        m = Mission(title="Teste", status=MissionStatus.COMPLETED)
        assert m.is_done

    def test_current_step(self):
        s1 = MissionStep(description="passo 1")
        s2 = MissionStep(description="passo 2")
        m = Mission(title="Teste", plan=[s1, s2], current_step=1)
        assert m.current().description == "passo 2"

    def test_current_none_when_empty(self):
        m = Mission(title="Teste")
        assert m.current() is None

    def test_summary_format(self):
        m = Mission(title="Projeto X", plan=[MissionStep(description="Passo A")])
        summary = m.summary()
        assert "Projeto X" in summary
        assert "Passo A" in summary


# ── MissionQueue ───────────────────────────────────────────────────────────────

class TestMissionQueue:
    def test_save_and_get(self, queue):
        m = Mission(title="Missão Test")
        queue.save(m)
        loaded = queue.get(m.id)
        assert loaded is not None
        assert loaded.title == "Missão Test"

    def test_save_updates_updated_at(self, queue):
        m = Mission(title="Missão Update")
        queue.save(m)
        t1 = m.updated_at
        queue.save(m)
        assert m.updated_at >= t1

    def test_list_active(self, queue):
        m1 = Mission(title="Ativa", status=MissionStatus.RUNNING)
        m2 = Mission(title="Concluída", status=MissionStatus.COMPLETED)
        queue.save(m1)
        queue.save(m2)
        active = queue.list_active()
        ids = [m.id for m in active]
        assert m1.id in ids
        assert m2.id not in ids

    def test_plan_serialization(self, queue):
        step = MissionStep(description="Serializar", tool="wind_chat")
        m = Mission(title="Serialização", plan=[step])
        queue.save(m)
        loaded = queue.get(m.id)
        assert len(loaded.plan) == 1
        assert loaded.plan[0].description == "Serializar"

    def test_get_nonexistent(self, queue):
        assert queue.get("id-que-nao-existe") is None


# ── MissionEngine ──────────────────────────────────────────────────────────────

class TestMissionEngine:
    def test_create_persists(self, engine, queue):
        m = engine.create("Nova Missão", steps=[{"description": "Passo 1"}])
        assert queue.get(m.id) is not None

    def test_run_all_steps(self, engine):
        calls = []

        def dummy_tool(step, ctx):
            calls.append(step.description)
            return {"done": True}

        engine.register_tool("wind_chat", dummy_tool)
        m = engine.create("Missão Teste", steps=[
            {"description": "A", "tool": "wind_chat"},
            {"description": "B", "tool": "wind_chat"},
        ])
        result = engine.run(m)
        assert result.status == MissionStatus.COMPLETED
        assert calls == ["A", "B"]

    def test_run_fails_on_tool_error(self, engine):
        def bad_tool(step, ctx):
            raise ValueError("Erro simulado")

        engine.register_tool("wind_chat", bad_tool)
        m = engine.create("Missão Falha", steps=[{"description": "X", "tool": "wind_chat"}])
        result = engine.run(m)
        assert result.status == MissionStatus.FAILED
        assert result.plan[0].error == "Erro simulado"

    def test_unregistered_tool_fails(self, engine):
        m = engine.create("Sem tool", steps=[{"description": "Y", "tool": "ferramenta_inexistente"}])
        result = engine.run(m)
        assert result.status == MissionStatus.FAILED

    def test_pause_and_resume(self, engine):
        calls = []

        def slow_tool(step, ctx):
            calls.append(step.description)
            return {}

        engine.register_tool("wind_chat", slow_tool)
        m = engine.create("Pausável", steps=[
            {"description": "P1", "tool": "wind_chat"},
            {"description": "P2", "tool": "wind_chat"},
        ])
        # Executar apenas criação; pausar
        engine.pause(m)
        assert m.status == MissionStatus.PAUSED

        # Retomar
        engine.resume(m.id)
        assert len(calls) == 2

    def test_cancel(self, engine):
        m = engine.create("Cancelável", steps=[])
        engine.cancel(m)
        assert m.status == MissionStatus.CANCELLED
