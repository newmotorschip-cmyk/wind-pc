"""
Testes unitários — ProjectCard, ProjectStore e ProjectManager (Fase 2).
"""
import pytest
from pathlib import Path

from src.projects.project import ProjectCard, ProjectStatus
from src.projects.store import ProjectStore
from src.projects.manager import ProjectManager


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_projects.db"


@pytest.fixture
def store(tmp_db):
    return ProjectStore(tmp_db)


@pytest.fixture
def manager(store):
    return ProjectManager(store)


# ── ProjectCard ────────────────────────────────────────────────────────────────

class TestProjectCard:
    def test_add_decision(self):
        p = ProjectCard(name="Projeto X")
        p.add_decision("Usar SQLite", context="Simplicidade")
        assert len(p.decisions) == 1
        assert p.decisions[0]["text"] == "Usar SQLite"

    def test_summary_contains_name(self):
        p = ProjectCard(name="CARTECH", description="Ferramenta ECU")
        s = p.summary()
        assert "CARTECH" in s

    def test_default_status_active(self):
        p = ProjectCard(name="Novo")
        assert p.status == ProjectStatus.ACTIVE


# ── ProjectStore ───────────────────────────────────────────────────────────────

class TestProjectStore:
    def test_save_and_get(self, store):
        p = ProjectCard(name="CARTECH")
        store.save(p)
        loaded = store.get(p.id)
        assert loaded is not None
        assert loaded.name == "CARTECH"

    def test_get_nonexistent(self, store):
        assert store.get("id-invalido") is None

    def test_list_active(self, store):
        p1 = ProjectCard(name="Ativo")
        p2 = ProjectCard(name="Arquivado", status=ProjectStatus.ARCHIVED)
        store.save(p1)
        store.save(p2)
        active = store.list_active()
        names = [p.name for p in active]
        assert "Ativo" in names
        assert "Arquivado" not in names

    def test_search_by_name(self, store):
        store.save(ProjectCard(name="CARTECH-NetShare"))
        store.save(ProjectCard(name="BoxControl"))
        results = store.search_by_name("CARTECH")
        assert len(results) >= 1
        assert any("CARTECH" in r.name for r in results)

    def test_decisions_persisted(self, store):
        p = ProjectCard(name="Decisões")
        p.add_decision("Usar FTS5", "Performance de busca")
        store.save(p)
        loaded = store.get(p.id)
        assert len(loaded.decisions) == 1
        assert loaded.decisions[0]["text"] == "Usar FTS5"

    def test_tags_persisted(self, store):
        p = ProjectCard(name="Tags", tags=["ecu", "reprogram"])
        store.save(p)
        loaded = store.get(p.id)
        assert "ecu" in loaded.tags


# ── ProjectManager ─────────────────────────────────────────────────────────────

class TestProjectManager:
    def test_create(self, manager):
        p = manager.create("WIND Core", description="Motor da WIND")
        assert p.id
        assert p.name == "WIND Core"

    def test_find_exact(self, manager):
        manager.create("CARTECH")
        found = manager.find("CARTECH")
        assert found is not None
        assert found.name == "CARTECH"

    def test_find_case_insensitive(self, manager):
        manager.create("CARTECH")
        found = manager.find("cartech")
        assert found is not None

    def test_find_substring(self, manager):
        manager.create("CARTECH-NetShare")
        found = manager.find("NetShare")
        assert found is not None

    def test_find_fuzzy(self, manager):
        manager.create("BoxControl")
        found = manager.find("BoxControll")  # typo
        assert found is not None

    def test_find_not_found(self, manager):
        assert manager.find("ProjetoInexistente123") is None

    def test_update_next_action(self, manager):
        p = manager.create("Projeto A")
        manager.update_next_action(p.id, "Implementar autenticação")
        updated = manager.list_all()[0]
        assert updated.next_action == "Implementar autenticação"

    def test_continuation_context(self, manager):
        p = manager.create("CARTECH", description="ECU reprogram tool")
        p.add_decision("Usar SQLite")
        ctx = manager.continuation_context(p)
        assert "CARTECH" in ctx
        assert "ECU reprogram" in ctx
