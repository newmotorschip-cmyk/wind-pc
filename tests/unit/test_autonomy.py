"""Testes da Fase 8 — módulo de autonomia graduada."""
import json
from pathlib import Path

import pytest

from src.autonomy.level import AutonomyLevel, AutonomyProfile, LevelChange
from src.autonomy.decision import (
    DecisionRecord, DecisionStatus, DecisionStore, RiskLevel,
)
from src.autonomy.engine import DecisionEngine


# ── AutonomyLevel ──────────────────────────────────────────────────────────

def test_autonomy_level_values():
    assert AutonomyLevel.A0.value == "A0"
    assert AutonomyLevel.A4.value == "A4"


def test_autonomy_level_numeric():
    nums = [AutonomyLevel(f"A{i}").numeric() for i in range(5)]
    assert nums == list(range(5))


def test_autonomy_level_label_contains_value():
    for lvl in AutonomyLevel:
        assert lvl.value in lvl.label()


def test_allows_read():
    assert AutonomyLevel.A0.allows_read() is False   # A0 somente responde
    for lvl in [AutonomyLevel.A1, AutonomyLevel.A2, AutonomyLevel.A3, AutonomyLevel.A4]:
        assert lvl.allows_read() is True


def test_allows_isolated_write():
    assert AutonomyLevel.A0.allows_isolated_write() is False
    assert AutonomyLevel.A2.allows_isolated_write() is True
    assert AutonomyLevel.A3.allows_isolated_write() is True


def test_allows_project_write():
    assert AutonomyLevel.A2.allows_project_write() is False
    assert AutonomyLevel.A3.allows_project_write() is True
    assert AutonomyLevel.A4.allows_project_write() is True


def test_allows_external_action():
    assert AutonomyLevel.A3.allows_external_action() is False
    assert AutonomyLevel.A4.allows_external_action() is True


# ── AutonomyProfile ────────────────────────────────────────────────────────

def test_profile_default_level():
    p = AutonomyProfile()
    assert p.current_level == AutonomyLevel.A1


def test_profile_level_for_no_domain():
    p = AutonomyProfile()
    assert p.level_for() == AutonomyLevel.A1


def test_profile_level_for_domain_override():
    p = AutonomyProfile(domain_overrides={"re": "A2"})
    assert p.level_for("re") == AutonomyLevel.A2


def test_profile_level_for_unknown_domain_falls_back():
    p = AutonomyProfile()
    assert p.level_for("xyz") == AutonomyLevel.A1


def test_profile_demote_on_error():
    p = AutonomyProfile(current_level=AutonomyLevel.A3)
    change = p.demote_on_error("teste de erro")
    assert p.current_level == AutonomyLevel.A1
    assert change.to_level == AutonomyLevel.A1
    assert len(p.history) == 1


def test_profile_never_self_elevates():
    """Perfil nunca deve elevar nível por conta própria."""
    p = AutonomyProfile(current_level=AutonomyLevel.A1)
    # demote_on_error só rebaixa
    change = p.demote_on_error("algum erro")
    assert p.current_level == AutonomyLevel.A1  # já era A1, mantém


def test_profile_to_dict_from_dict():
    p = AutonomyProfile(current_level=AutonomyLevel.A2, domain_overrides={"re": "A3"})
    d = p.to_dict()
    p2 = AutonomyProfile.from_dict(d)
    assert p2.current_level == AutonomyLevel.A2
    assert p2.level_for("re") == AutonomyLevel.A3


def test_profile_save_load(tmp_path):
    path = tmp_path / "profile.json"
    p = AutonomyProfile(current_level=AutonomyLevel.A2)
    p.save(path)
    p2 = AutonomyProfile.load(path)
    assert p2.current_level == AutonomyLevel.A2


def test_profile_load_missing_file(tmp_path):
    path = tmp_path / "nonexistent.json"
    p = AutonomyProfile.load(path)
    assert p.current_level == AutonomyLevel.A1  # padrão


# ── RiskLevel ──────────────────────────────────────────────────────────────

def test_risk_numeric():
    assert RiskLevel.LOW.numeric() == 1
    assert RiskLevel.CRITICAL.numeric() == 4


# ── DecisionRecord ─────────────────────────────────────────────────────────

def _make_record(**kwargs) -> DecisionRecord:
    defaults = dict(
        id="test-id", request="testar algo", options=["opção A", "opção B"],
        evidence="evidência de teste", risk=RiskLevel.LOW,
        reversible=True, confidence=0.9, chosen_option="opção A",
        approved_by="", status=DecisionStatus.PENDING,
    )
    defaults.update(kwargs)
    return DecisionRecord(**defaults)


def test_decision_record_summary_contains_id():
    r = _make_record()
    assert "test-id"[:8] in r.summary()


def test_decision_record_to_dict_from_dict():
    r = _make_record(options=["A", "B"], status=DecisionStatus.APPROVED)
    d = r.to_dict()
    r2 = DecisionRecord.from_dict(d)
    assert r2.id == r.id
    assert r2.options == ["A", "B"]
    assert r2.status == DecisionStatus.APPROVED


# ── DecisionStore ──────────────────────────────────────────────────────────

@pytest.fixture
def decision_store(tmp_path):
    return DecisionStore(tmp_path / "test.db")


def test_store_save_and_get(decision_store):
    r = _make_record()
    decision_store.save(r)
    fetched = decision_store.get("test-id")
    assert fetched is not None
    assert fetched.id == "test-id"


def test_store_list_pending(decision_store):
    r1 = _make_record(id="a1", status=DecisionStatus.PENDING)
    r2 = _make_record(id="a2", status=DecisionStatus.APPROVED)
    decision_store.save(r1)
    decision_store.save(r2)
    pending = decision_store.list_pending()
    ids = [p.id for p in pending]
    assert "a1" in ids
    assert "a2" not in ids


def test_store_list_recent(decision_store):
    for i in range(5):
        decision_store.save(_make_record(id=f"r{i}"))
    recent = decision_store.list_recent(limit=3)
    assert len(recent) == 3


def test_store_stats(decision_store):
    decision_store.save(_make_record(id="s1", status=DecisionStatus.PENDING))
    decision_store.save(_make_record(id="s2", status=DecisionStatus.APPROVED, approved_by="Felipe"))
    stats = decision_store.stats()
    assert stats["total"] >= 2
    assert stats["approved_by_felipe"] >= 1


# ── DecisionEngine ─────────────────────────────────────────────────────────

@pytest.fixture
def engine(tmp_path):
    store   = DecisionStore(tmp_path / "test.db")
    profile = AutonomyProfile(current_level=AutonomyLevel.A2)
    return DecisionEngine(store, profile)


def test_engine_within_envelope_a2_low_risk(engine):
    ok, reason = engine.within_envelope(AutonomyLevel.A2, RiskLevel.LOW, 0.85, True)
    assert ok is True


def test_engine_outside_envelope_a2_high_risk(engine):
    ok, reason = engine.within_envelope(AutonomyLevel.A2, RiskLevel.HIGH, 0.85, True)
    assert ok is False


def test_engine_outside_envelope_a1(engine):
    ok, _ = engine.within_envelope(AutonomyLevel.A1, RiskLevel.LOW, 1.0, True)
    assert ok is False


def test_engine_a2_irreversible_blocked(engine):
    ok, _ = engine.within_envelope(AutonomyLevel.A2, RiskLevel.LOW, 0.85, False)
    assert ok is False


def test_engine_low_confidence_blocked(engine):
    ok, _ = engine.within_envelope(AutonomyLevel.A2, RiskLevel.LOW, 0.5, True)
    assert ok is False


def test_engine_evaluate_autonomous_a2(engine):
    record = engine.evaluate(
        request="tarefa leve", options=["A"], evidence="ok",
        risk=RiskLevel.LOW, reversible=True, confidence=0.9,
    )
    assert record.status == DecisionStatus.APPROVED
    assert record.approved_by == ""  # autonomia sem aprovação explícita


def test_engine_evaluate_pending_a1(tmp_path):
    store   = DecisionStore(tmp_path / "db.db")
    profile = AutonomyProfile(current_level=AutonomyLevel.A1)
    eng     = DecisionEngine(store, profile)
    record  = eng.evaluate(
        request="tarefa qualquer", options=["A"], evidence="x",
        risk=RiskLevel.LOW, reversible=True, confidence=0.9,
    )
    assert record.status == DecisionStatus.PENDING


def test_engine_approve(engine):
    record = engine.evaluate(
        request="algo complexo", options=["A"], evidence="evidencia",
        risk=RiskLevel.HIGH, reversible=False, confidence=0.9,
    )
    assert record.status == DecisionStatus.PENDING
    approved = engine.approve(record.id, approved_by="Felipe")
    assert approved is not None
    assert approved.status == DecisionStatus.APPROVED
    assert approved.approved_by == "Felipe"


def test_engine_reject(engine):
    record = engine.evaluate(
        request="algo", options=["A"], evidence="x",
        risk=RiskLevel.HIGH, reversible=False, confidence=0.9,
    )
    rejected = engine.reject(record.id, reason="Não adequado")
    assert rejected.status == DecisionStatus.REJECTED


def test_engine_mark_executed(engine):
    record = engine.evaluate(
        request="tarefa leve", options=["A"], evidence="ok",
        risk=RiskLevel.LOW, reversible=True, confidence=0.9,
    )
    executed = engine.mark_executed(record.id, result="Concluído")
    assert executed.status == DecisionStatus.EXECUTED


def test_engine_register_error_demotes(engine):
    assert engine.profile.current_level == AutonomyLevel.A2
    engine.register_error("erro grave")
    assert engine.profile.current_level == AutonomyLevel.A1


def test_engine_pending_summary_empty(engine):
    summary = engine.pending_summary()
    assert "nenhuma" in summary.lower()


def test_engine_pending_summary_with_records(engine):
    engine.evaluate(
        request="algo complexo", options=["A"], evidence="x",
        risk=RiskLevel.HIGH, reversible=False, confidence=0.9,
    )
    summary = engine.pending_summary()
    assert "pendente" in summary.lower()


def test_engine_context_for_orchestrator(engine):
    ctx = engine.context_for_orchestrator()
    assert "A2" in ctx or "autonomia" in ctx.lower()


def test_engine_a4_always_pending(tmp_path):
    """A4 nunca age autonomamente — sempre exige aprovação por operação."""
    store   = DecisionStore(tmp_path / "db.db")
    profile = AutonomyProfile(current_level=AutonomyLevel.A4)
    eng     = DecisionEngine(store, profile)
    record  = eng.evaluate(
        request="ação crítica", options=["A"], evidence="ok",
        risk=RiskLevel.LOW, reversible=True, confidence=1.0,
    )
    assert record.status == DecisionStatus.PENDING
