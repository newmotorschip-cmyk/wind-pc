"""
Testes unitários — Fase 3: ServiceCase, CaseStore, CaseManager, Anonymizer.
"""
import pytest
from pathlib import Path

from src.cases.case import (
    CaseResult, CaseStatus, EcuInfo, ServiceCase, VehicleInfo,
)
from src.cases.store import CaseStore
from src.cases.manager import CaseManager, CLOSING_QUESTIONS
from src.cases.anonymizer import anonymize_text, anonymize_case_for_remote


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_cases.db"


@pytest.fixture
def store(tmp_db):
    return CaseStore(tmp_db)


@pytest.fixture
def manager(store):
    return CaseManager(store)


def _make_case(queixa="Motor falhando em aceleração") -> ServiceCase:
    return ServiceCase(
        queixa=queixa,
        vehicle=VehicleInfo(marca="Volkswagen", modelo="Golf", ano=2018, motor="EA888"),
        ecu=EcuInfo(fabricante="Bosch", referencia="MED17.5", versao_sw="1.0"),
        dtcs=["P0300", "P0301"],
    )


# ── VehicleInfo ───────────────────────────────────────────────────────────────

class TestVehicleInfo:
    def test_anonymized_removes_placa_vin(self):
        v = VehicleInfo(placa="ABC1D23", vin="1HGCM82633A004352", marca="Honda", modelo="Civic")
        a = v.anonymized()
        assert a.placa == "[REDACTED]"
        assert a.vin == "[REDACTED]"
        assert a.marca == "Honda"
        assert a.modelo == "Civic"

    def test_round_trip(self):
        v = VehicleInfo(marca="BMW", modelo="X5", ano=2020, motor="B57")
        assert VehicleInfo.from_dict(v.to_dict()).marca == "BMW"


# ── ServiceCase ───────────────────────────────────────────────────────────────

class TestServiceCase:
    def test_add_action(self):
        c = _make_case()
        c.add_action("Leitura de DTCs", "P0300 presente")
        assert len(c.actions) == 1
        assert c.actions[0]["description"] == "Leitura de DTCs"

    def test_close_sets_status(self):
        c = _make_case()
        c.close(CaseResult.SUCCESS, what_worked="Troca do injetor 1")
        assert c.status == CaseStatus.CLOSED
        assert c.result == CaseResult.SUCCESS
        assert "Troca do injetor 1" in c.lessons

    def test_close_ignores_blank_lessons(self):
        c = _make_case()
        c.close(CaseResult.SUCCESS, what_worked="OK", what_surprised="", repeat_next_time="")
        assert len(c.lessons) == 1  # só a não-vazia

    def test_similarity_text_no_pii(self):
        c = _make_case()
        c.vehicle.placa = "ABC1D23"
        c.vehicle.vin   = "1HGCM82633A004352"
        text = c.similarity_text()
        assert "ABC1D23" not in text
        assert "1HGCM82633A004352" not in text
        assert "Golf" in text
        assert "P0300" in text

    def test_summary_pii_hidden_by_default(self):
        c = _make_case()
        c.vehicle.placa = "ABC1D23"
        s = c.summary(include_pii=False)
        assert "[REDACTED]" in s or "ABC1D23" not in s

    def test_default_status_open(self):
        c = _make_case()
        assert c.status == CaseStatus.OPEN


# ── CaseStore ─────────────────────────────────────────────────────────────────

class TestCaseStore:
    def test_save_and_get(self, store):
        c = _make_case()
        store.save(c)
        loaded = store.get(c.id)
        assert loaded is not None
        assert loaded.queixa == c.queixa
        assert loaded.dtcs == ["P0300", "P0301"]

    def test_get_nonexistent(self, store):
        assert store.get("nao-existe") is None

    def test_list_open(self, store):
        c1 = _make_case("Falha 1")
        c2 = _make_case("Falha 2")
        c2.status = CaseStatus.CLOSED
        store.save(c1)
        store.save(c2)
        open_cases = store.list_open()
        ids = [c.id for c in open_cases]
        assert c1.id in ids
        assert c2.id not in ids

    def test_search_similar_by_model(self, store):
        c = _make_case("Falha de injeção")
        store.save(c)
        results = store.search_similar("Golf EA888 injeção")
        assert any(r.id == c.id for r in results)

    def test_vehicle_persisted(self, store):
        c = _make_case()
        store.save(c)
        loaded = store.get(c.id)
        assert loaded.vehicle.marca == "Volkswagen"
        assert loaded.vehicle.ano == 2018

    def test_ecu_persisted(self, store):
        c = _make_case()
        store.save(c)
        loaded = store.get(c.id)
        assert loaded.ecu.fabricante == "Bosch"
        assert loaded.ecu.referencia == "MED17.5"

    def test_lessons_persisted_after_close(self, store):
        c = _make_case()
        c.close(CaseResult.SUCCESS, what_worked="Limpeza do injetor")
        store.save(c)
        loaded = store.get(c.id)
        assert "Limpeza do injetor" in loaded.lessons


# ── CaseManager ───────────────────────────────────────────────────────────────

class TestCaseManager:
    def test_open_creates_case(self, manager):
        c = manager.open("Falha intermitente")
        assert c.status == CaseStatus.OPEN
        assert c.queixa == "Falha intermitente"

    def test_close_case(self, manager):
        c = manager.open("Ruído no motor")
        closed = manager.close(c.id, result=CaseResult.SUCCESS, what_worked="Troca do rolamento")
        assert closed is not None
        assert closed.status == CaseStatus.CLOSED

    def test_close_nonexistent_returns_none(self, manager):
        result = manager.close("id-invalido")
        assert result is None

    def test_find_similar_returns_matching(self, manager):
        c = manager.open(
            "Falha de aceleração",
            vehicle=VehicleInfo(marca="Volkswagen", modelo="Golf", motor="EA888"),
            ecu=EcuInfo(referencia="MED17.5"),
        )
        similar = manager.find_similar(
            "Falha aceleração",
            vehicle=VehicleInfo(marca="Volkswagen", modelo="Golf"),
        )
        assert any(s.id == c.id for s in similar)

    def test_similar_context_no_pii(self, manager):
        c = manager.open("Defeito", vehicle=VehicleInfo(placa="XYZ9876", marca="Ford"))
        similar = [c]
        ctx = manager.similar_context(similar)
        assert "XYZ9876" not in ctx
        assert "[REDACTED]" in ctx or "Ford" in ctx

    def test_add_action(self, manager):
        c = manager.open("Teste ação")
        manager.add_action(c.id, "Verificação de pressão", "120 bar")
        updated = manager.get(c.id)
        assert len(updated.actions) == 1

    def test_closing_questions_count(self):
        assert len(CLOSING_QUESTIONS) == 3


# ── Anonymizer ────────────────────────────────────────────────────────────────

class TestAnonymizer:
    def test_placa_mercosul(self):
        result = anonymize_text("Veículo BRA2E19 apresentou falha")
        assert "BRA2E19" not in result
        assert "[PLACA]" in result

    def test_placa_antiga(self):
        result = anonymize_text("Placa ABC-1234 com defeito")
        assert "ABC-1234" not in result

    def test_vin_removed(self):
        result = anonymize_text("VIN: 1HGCM82633A004352")
        assert "1HGCM82633A004352" not in result
        assert "[VIN]" in result

    def test_cpf_removed(self):
        result = anonymize_text("CPF 123.456.789-09 do cliente")
        assert "123.456.789-09" not in result

    def test_preserves_technical_data(self):
        text = "DTCs P0300 P0301 na ECU MED17.5 do Golf EA888"
        result = anonymize_text(text)
        assert "P0300" in result
        assert "MED17.5" in result
        assert "Golf" in result

    def test_anonymize_case_dict(self):
        d = {
            "vehicle": {"placa": "ABC1D23", "vin": "1HGCM82633A004352", "marca": "VW"},
            "queixa": "Falha no veículo BRA2E19",
            "actions": [{"description": "Verificação placa ABC1D23"}],
            "lessons": ["Trocar o rolamento da placa ABC1D23"],
        }
        anon = anonymize_case_for_remote(d)
        assert anon["vehicle"]["placa"] == "[REDACTED]"
        assert anon["vehicle"]["vin"] == "[REDACTED]"
        assert anon["vehicle"]["marca"] == "VW"  # técnico preservado
        assert "BRA2E19" not in anon["queixa"]
