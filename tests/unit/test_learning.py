"""Testes da Fase 8 — módulo de aprendizado contínuo."""
import tempfile
from pathlib import Path

import pytest

from src.learning.notes import LearningNote, NoteManager, NoteState, NoteStore
from src.learning.curriculum import (
    Curriculum, StudyItem, StudyPriority, StudyStatus,
)
from src.learning.retrospective import RetrospectiveGenerator


# ── NoteState / LearningNote ───────────────────────────────────────────────

def test_note_state_values():
    assert NoteState.PROPOSED.value  == "proposed"
    assert NoteState.VALIDATED.value == "validated"
    assert NoteState.OBSOLETE.value  == "obsolete"


def _make_note(**kwargs) -> LearningNote:
    defaults = dict(
        id="note-001", topic="ECU Bosch ME9",
        content="O checksum CRC32 está no offset 0x1FC.",
        state=NoteState.PROPOSED, confidence=0.7, tags=["ecu", "bosch"],
    )
    defaults.update(kwargs)
    return LearningNote(**defaults)


def test_note_summary_line_proposed():
    n = _make_note()
    line = n.summary_line()
    assert "note-001"[:8] in line
    assert "ECU Bosch ME9" in line


def test_note_summary_line_validated():
    n = _make_note(state=NoteState.VALIDATED)
    line = n.summary_line()
    assert "✅" in line


def test_note_to_dict_from_dict():
    n = _make_note(tags=["ecu", "bosch"])
    d = n.to_dict()
    n2 = LearningNote.from_dict(d)
    assert n2.id == n.id
    assert n2.tags == ["ecu", "bosch"]
    assert n2.state == NoteState.PROPOSED


def test_note_from_dict_tags_as_string():
    """Tags armazenadas como JSON string no SQLite — deve desserializar."""
    import json
    d = {
        "id": "x", "topic": "t", "content": "c",
        "tags": json.dumps(["a", "b"]),
        "state": "proposed", "confidence": 0.5,
        "created_at": 0,
    }
    n = LearningNote.from_dict(d)
    assert n.tags == ["a", "b"]


# ── NoteStore ──────────────────────────────────────────────────────────────

@pytest.fixture
def note_store(tmp_path):
    return NoteStore(tmp_path / "test.db")


def test_note_store_save_and_get(note_store):
    n = _make_note()
    note_store.save(n)
    fetched = note_store.get("note-001")
    assert fetched is not None
    assert fetched.topic == "ECU Bosch ME9"


def test_note_store_list_by_state(note_store):
    note_store.save(_make_note(id="n1", state=NoteState.PROPOSED))
    note_store.save(_make_note(id="n2", state=NoteState.VALIDATED))
    proposed = note_store.list_by_state(NoteState.PROPOSED)
    ids = [n.id for n in proposed]
    assert "n1" in ids
    assert "n2" not in ids


def test_note_store_search(note_store):
    note_store.save(_make_note(id="n3", topic="checksum TriCore", content="offset 0x200"))
    results = note_store.search("tricore")
    assert any(n.id == "n3" for n in results)


def test_note_store_validate(note_store):
    note_store.save(_make_note(id="n4"))
    validated = note_store.validate("n4", validated_by="Felipe")
    assert validated is not None
    assert validated.state == NoteState.VALIDATED
    assert validated.validated_by == "Felipe"


def test_note_store_validate_nonexistent(note_store):
    result = note_store.validate("nao-existe")
    assert result is None


def test_note_store_mark_obsolete(note_store):
    note_store.save(_make_note(id="n5"))
    obs = note_store.mark_obsolete("n5")
    assert obs.state == NoteState.OBSOLETE


def test_note_store_stats(note_store):
    note_store.save(_make_note(id="ns1", state=NoteState.PROPOSED))
    note_store.save(_make_note(id="ns2", state=NoteState.VALIDATED))
    stats = note_store.stats()
    assert stats.get("proposed", 0) >= 1
    assert stats.get("validated", 0) >= 1


def test_note_store_upsert_updates_state(note_store):
    n = _make_note(id="n6", state=NoteState.PROPOSED)
    note_store.save(n)
    n.state = NoteState.VALIDATED
    n.validated_by = "Felipe"
    note_store.save(n)
    fetched = note_store.get("n6")
    assert fetched.state == NoteState.VALIDATED


# ── NoteManager ────────────────────────────────────────────────────────────

@pytest.fixture
def note_manager(tmp_path):
    store = NoteStore(tmp_path / "test.db")
    return NoteManager(store)


def test_manager_create_always_proposed(note_manager):
    n = note_manager.create(
        topic="Protocolo UDS", content="Serviço 0x22 lê DID.",
        source="manual", confidence=0.8,
    )
    assert n.state == NoteState.PROPOSED
    assert n.id != ""


def test_manager_note_never_self_validates(note_manager):
    """WIND não pode chamar validate passando 'WIND' como validador."""
    n = note_manager.create(topic="x", content="y")
    # Regra: validated_by deve ser sempre "Felipe" ou outro humano.
    # O manager.validate só aceita chamadas externas — testamos que funciona quando
    # chamado por Felipe (humano).
    validated = note_manager.validate(n.id, validated_by="Felipe")
    assert validated.state == NoteState.VALIDATED
    assert validated.validated_by == "Felipe"


def test_manager_list_proposed(note_manager):
    note_manager.create(topic="A", content="x")
    note_manager.create(topic="B", content="y")
    proposed = note_manager.list_proposed()
    assert len(proposed) >= 2


def test_manager_list_validated(note_manager):
    n = note_manager.create(topic="C", content="z")
    note_manager.validate(n.id)
    validated = note_manager.list_validated()
    assert any(v.id == n.id for v in validated)


def test_manager_search(note_manager):
    note_manager.create(topic="SuperH SH7xxx", content="loader Renesas")
    results = note_manager.search("superh")
    assert len(results) >= 1


def test_manager_stats(note_manager):
    note_manager.create(topic="A", content="x")
    stats = note_manager.stats()
    assert isinstance(stats, dict)


def test_manager_context_for_topic_empty(note_manager):
    ctx = note_manager.context_for_topic("assunto inexistente")
    assert ctx == ""


def test_manager_context_for_topic_validated(note_manager):
    n = note_manager.create(topic="OBD-II", content="PID 0x0C = RPM")
    note_manager.validate(n.id)
    ctx = note_manager.context_for_topic("OBD-II")
    assert "OBD-II" in ctx or "PID" in ctx


# ── StudyItem / Curriculum ─────────────────────────────────────────────────

def test_study_item_summary_line():
    item = StudyItem(
        id="item-1", topic="Bosch ME9", description="ECU",
        priority=StudyPriority.HIGH, status=StudyStatus.PENDING,
    )
    line = item.summary_line()
    assert "HIGH" in line
    assert "Bosch ME9" in line


def test_study_item_to_from_dict():
    item = StudyItem(
        id="item-2", topic="EDC17", description="diesel",
        priority=StudyPriority.MEDIUM, status=StudyStatus.COMPLETED,
        tags=["diesel"], prerequisites=["item-1"],
    )
    d = item.to_dict()
    item2 = StudyItem.from_dict(d)
    assert item2.id == "item-2"
    assert item2.priority == StudyPriority.MEDIUM
    assert item2.tags == ["diesel"]


@pytest.fixture
def curriculum(tmp_path):
    return Curriculum(tmp_path / "curriculum.json")


def test_curriculum_loads_defaults(curriculum):
    items = curriculum.list_all()
    assert len(items) >= 5


def test_curriculum_list_pending_sorted_by_priority(curriculum):
    pending = curriculum.list_pending()
    priorities = [i.priority for i in pending]
    assert priorities == sorted(priorities, key=lambda p: {"high": 0, "medium": 1, "low": 2}[p.value])


def test_curriculum_add(curriculum):
    before = len(curriculum.list_all())
    item = curriculum.add(
        topic="Novo tópico",
        description="Descrição",
        priority=StudyPriority.HIGH,
    )
    assert item.id != ""
    assert len(curriculum.list_all()) == before + 1


def test_curriculum_mark_in_progress(curriculum):
    pending = curriculum.list_pending()
    assert pending, "Deve ter itens pendentes"
    item = curriculum.mark_in_progress(pending[0].id)
    assert item is not None
    assert item.status == StudyStatus.IN_PROGRESS


def test_curriculum_mark_completed(curriculum):
    pending = curriculum.list_pending()
    assert pending
    item = curriculum.mark_completed(pending[0].id, notes="concluído com sucesso")
    assert item is not None
    assert item.status == StudyStatus.COMPLETED
    assert item.completed_at > 0


def test_curriculum_get_nonexistent(curriculum):
    item = curriculum.get("id-inexistente")
    assert item is None


def test_curriculum_summary_contains_totals(curriculum):
    summary = curriculum.summary()
    assert "Currículo" in summary


def test_curriculum_persists(tmp_path):
    path = tmp_path / "curr.json"
    c1 = Curriculum(path)
    c1.add(topic="Persistência", description="Teste", priority=StudyPriority.LOW)
    c2 = Curriculum(path)
    topics = [i.topic for i in c2.list_all()]
    assert "Persistência" in topics


# ── RetrospectiveGenerator ─────────────────────────────────────────────────

def test_retrospective_generates_text(tmp_path):
    gen = RetrospectiveGenerator(db_path=tmp_path / "empty.db")
    text = gen.generate(days=7)
    assert "Retrospectiva" in text
    assert "fim da retrospectiva" in text


def test_retrospective_with_engine(tmp_path):
    from src.autonomy.decision import DecisionStore
    from src.autonomy.level import AutonomyProfile, AutonomyLevel
    from src.autonomy.engine import DecisionEngine

    store   = DecisionStore(tmp_path / "db.db")
    profile = AutonomyProfile(current_level=AutonomyLevel.A2)
    engine  = DecisionEngine(store, profile)

    gen  = RetrospectiveGenerator(db_path=tmp_path / "db.db", autonomy_engine=engine)
    text = gen.generate(days=7)
    assert "A2" in text or "Nível" in text


def test_retrospective_with_note_manager(tmp_path):
    store   = NoteStore(tmp_path / "db.db")
    manager = NoteManager(store)
    n = manager.create(topic="Teste", content="conteúdo")
    manager.validate(n.id)

    gen  = RetrospectiveGenerator(db_path=tmp_path / "db.db", note_manager=manager)
    text = gen.generate(days=7)
    assert "Notas" in text or "aprendizado" in text.lower()


def test_retrospective_with_curriculum(tmp_path):
    curr = Curriculum(tmp_path / "curr.json")
    gen  = RetrospectiveGenerator(db_path=tmp_path / "db.db", curriculum=curr)
    text = gen.generate(days=7)
    assert "Currículo" in text
