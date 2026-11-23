"""
Testes unitários — Fase 5: Calibração ECU.
Todos com dados sintéticos — nunca dados reais de cliente ou firmware real.
"""
import tempfile
from pathlib import Path

import pytest

from src.calibration.ecu_families import (
    EcuFamily, get_family, list_families, search_families,
)
from src.calibration.map_taxonomy import (
    MapCategory, MapDefinition, guardian_level_for_map, list_maps, get_map,
)
from src.calibration.proposal import (
    CalibrationProposal, MapDelta, ProposalStatus,
)
from src.calibration.checksum import ChecksumAlgorithm, ChecksumVerifier
from src.calibration.store import CalibrationStore
from src.calibration.manager import CalibrationManager, CalibrationError


# ── EcuFamilies ───────────────────────────────────────────────────────────────

class TestEcuFamilies:
    def test_list_families_not_empty(self):
        assert len(list_families()) >= 5

    def test_bosch_me9_present(self):
        f = get_family("bosch_me9")
        assert f is not None
        assert f.manufacturer == "Bosch"
        assert "TriCore" in " ".join(f.architectures)

    def test_bosch_med17_present(self):
        f = get_family("bosch_med17")
        assert f is not None
        assert "MED" in f.series

    def test_delphi_hcs12_present(self):
        f = get_family("delphi_mt20u2")
        assert f is not None
        assert "HCS12" in " ".join(f.architectures)

    def test_get_family_missing_returns_none(self):
        assert get_family("familia_inexistente") is None

    def test_search_by_manufacturer(self):
        results = search_families("bosch")
        assert len(results) >= 2
        assert all("Bosch" in r.manufacturer for r in results)

    def test_search_by_architecture(self):
        results = search_families("tricore")
        assert len(results) >= 2

    def test_search_by_series(self):
        results = search_families("EDC")
        assert any("EDC" in r.series for r in results)

    def test_summary_line_format(self):
        f = get_family("bosch_me9")
        line = f.summary_line()
        assert "Bosch" in line
        assert "ME 9" in line


# ── MapTaxonomy ───────────────────────────────────────────────────────────────

class TestMapTaxonomy:
    def test_list_all_maps_not_empty(self):
        assert len(list_maps()) >= 10

    def test_emission_maps_guardian_level_4(self):
        for m in list_maps(MapCategory.EMISSION):
            assert m.guardian_level == 4

    def test_immobilizer_guardian_level_4(self):
        for m in list_maps(MapCategory.IMMOBILIZER):
            assert m.guardian_level == 4

    def test_odometer_guardian_level_4(self):
        for m in list_maps(MapCategory.ODOMETER):
            assert m.guardian_level == 4

    def test_fueling_guardian_level_2(self):
        for m in list_maps(MapCategory.FUELING):
            assert m.guardian_level == 2

    def test_limiters_guardian_level_3(self):
        for m in list_maps(MapCategory.LIMITERS):
            assert m.guardian_level >= 3

    def test_requires_legal_note_emission(self):
        m = get_map("egr_rate_setpoint")
        assert m is not None
        assert m.requires_legal_note is True

    def test_no_legal_note_for_ignition(self):
        m = get_map("ignition_advance_base")
        assert m is not None
        assert m.requires_legal_note is False

    def test_guardian_level_for_map_unknown(self):
        assert guardian_level_for_map("mapa_inexistente") == 2

    def test_summary_line_contains_legal(self):
        m = get_map("egr_rate_setpoint")
        assert "LEGAL" in m.summary_line()

    def test_filter_by_category(self):
        ignition = list_maps(MapCategory.IGNITION)
        assert all(m.category == MapCategory.IGNITION for m in ignition)


# ── CalibrationProposal ───────────────────────────────────────────────────────

class TestCalibrationProposal:
    def _make_delta(self, map_name: str = "injection_quantity_base") -> MapDelta:
        return MapDelta(
            map_name=map_name,
            description="Teste",
            unit="mg/stk",
            original_values=[10.0, 20.0, 30.0],
            proposed_values=[11.0, 22.0, 33.0],
        )

    def test_map_delta_max_percent(self):
        d = self._make_delta()
        assert d.max_delta_percent > 0.0
        assert d.max_delta_percent < 20.0

    def test_map_delta_zero_original_no_crash(self):
        d = MapDelta("test", "t", "u", [0.0, 1.0], [0.0, 1.1])
        assert d.max_delta_percent >= 0.0

    def test_proposal_serialization(self):
        d = self._make_delta()
        p = CalibrationProposal(
            id="test-id-1",
            ecu_family_id="bosch_me9",
            vehicle_description="VW Golf 2.0 TDI",
            maps=[d],
            justification="Mais torque",
            validation_plan="Datalog em bancada",
            guardian_level=2,
            requires_legal_note=False,
            legal_note="",
            status=ProposalStatus.PENDING,
            created_at=1000.0,
            session_id="sess1",
        )
        d2 = p.to_dict()
        p2 = CalibrationProposal.from_dict(d2)
        assert p2.id == p.id
        assert p2.maps[0].map_name == "injection_quantity_base"

    def test_proposal_summary_no_legal(self):
        d = self._make_delta()
        p = CalibrationProposal(
            id="x", ecu_family_id="bosch_me9",
            vehicle_description="VW Golf", maps=[d],
            justification="j", validation_plan="v",
            guardian_level=2, requires_legal_note=False, legal_note="",
            status=ProposalStatus.PENDING, created_at=0.0, session_id="",
        )
        summary = p.summary()
        assert "injection_quantity_base" in summary
        assert "Guardian: 2" in summary

    def test_proposal_summary_with_legal(self):
        d = self._make_delta("egr_rate_setpoint")
        p = CalibrationProposal(
            id="x", ecu_family_id="bosch_edc16",
            vehicle_description="Audi A3 2.0 TDI", maps=[d],
            justification="Remoção EGR", validation_plan="Revisão emissões",
            guardian_level=4, requires_legal_note=True,
            legal_note="Autorizado por Felipe — dono do veículo.",
            status=ProposalStatus.PENDING, created_at=0.0, session_id="",
        )
        summary = p.summary()
        assert "LEGAL" in summary


# ── Checksum ──────────────────────────────────────────────────────────────────

class TestChecksum:
    def test_crc32_known_family_bosch(self):
        cv = ChecksumVerifier()
        result = cv.verify(b"\x00" * 1024, "bosch_med17")
        assert result.algorithm == ChecksumAlgorithm.CRC32_BOSCH
        assert result.computed is not None
        assert result.valid is True  # cálculo OK, sem referência

    def test_sum8_delphi(self):
        cv = ChecksumVerifier()
        result = cv.verify(b"\x01\x02\x03", "delphi_mt20u2")
        assert result.algorithm == ChecksumAlgorithm.SUM8
        assert result.computed == (1 + 2 + 3) & 0xFF

    def test_sum16_denso(self):
        cv = ChecksumVerifier()
        data = b"\x00\x01\x00\x02"
        result = cv.verify(data, "denso_sh7xxx")
        assert result.algorithm == ChecksumAlgorithm.SUM16
        assert result.computed == (1 + 2) & 0xFFFF

    def test_unknown_family_returns_unknown(self):
        cv = ChecksumVerifier()
        result = cv.verify(b"\x00" * 64, "familia_desconhecida")
        assert result.algorithm == ChecksumAlgorithm.UNKNOWN
        assert result.valid is False

    def test_verify_with_expected_match(self):
        import zlib
        cv = ChecksumVerifier()
        data = b"\xAA\xBB\xCC\xDD" * 256
        expected = zlib.crc32(data) & 0xFFFFFFFF
        result = cv.verify_with_expected(data, "bosch_me9", expected)
        assert result.valid is True

    def test_verify_with_expected_mismatch(self):
        cv = ChecksumVerifier()
        result = cv.verify_with_expected(b"\x00" * 64, "bosch_me9", 0xDEADBEEF)
        assert result.valid is False
        assert "0xDEADBEEF" in result.notes.upper() or result.expected == 0xDEADBEEF

    def test_summary_line_ok(self):
        import zlib
        cv = ChecksumVerifier()
        data = b"\x01" * 64
        expected = zlib.crc32(data) & 0xFFFFFFFF
        result = cv.verify_with_expected(data, "bosch_me9", expected)
        assert "✅" in result.summary_line()

    def test_summary_line_no_ref(self):
        cv = ChecksumVerifier()
        result = cv.verify(b"\x00" * 64, "bosch_me9")
        assert "❓" in result.summary_line()


# ── CalibrationStore ──────────────────────────────────────────────────────────

class TestCalibrationStore:
    def _store(self, tmp_path) -> CalibrationStore:
        return CalibrationStore(tmp_path / "test.db")

    def _proposal(self, status=ProposalStatus.PENDING) -> CalibrationProposal:
        d = MapDelta("injection_quantity_base", "inj", "mg/stk",
                     [10.0], [11.0])
        return CalibrationProposal(
            id="p-001", ecu_family_id="bosch_me9",
            vehicle_description="Golf TDI",
            maps=[d], justification="j", validation_plan="v",
            guardian_level=2, requires_legal_note=False, legal_note="",
            status=status, created_at=1.0, session_id="s1",
        )

    def test_save_and_retrieve(self, tmp_path):
        store = self._store(tmp_path)
        p = self._proposal()
        store.save(p)
        p2 = store.get("p-001")
        assert p2 is not None
        assert p2.ecu_family_id == "bosch_me9"
        assert p2.maps[0].map_name == "injection_quantity_base"

    def test_list_pending(self, tmp_path):
        store = self._store(tmp_path)
        store.save(self._proposal(ProposalStatus.PENDING))
        store.save(CalibrationProposal(
            id="p-002", ecu_family_id="bosch_edc17",
            vehicle_description="BMW 320d",
            maps=[MapDelta("boost_pressure_setpoint", "b", "mbar", [1800.0], [1900.0])],
            justification="j2", validation_plan="v2",
            guardian_level=2, requires_legal_note=False, legal_note="",
            status=ProposalStatus.APPROVED, created_at=2.0, session_id="s2",
        ))
        pending = store.list_pending()
        assert len(pending) == 1
        assert pending[0].id == "p-001"

    def test_list_by_ecu(self, tmp_path):
        store = self._store(tmp_path)
        store.save(self._proposal())
        store.save(CalibrationProposal(
            id="p-003", ecu_family_id="delphi_mt20u2",
            vehicle_description="Celta",
            maps=[MapDelta("injection_quantity_base", "inj", "mg/stk", [5.0], [5.5])],
            justification="j3", validation_plan="v3",
            guardian_level=2, requires_legal_note=False, legal_note="",
            status=ProposalStatus.PENDING, created_at=3.0, session_id="s3",
        ))
        bosch_props = store.list_by_ecu("bosch_me9")
        assert len(bosch_props) == 1


# ── CalibrationManager ────────────────────────────────────────────────────────

class TestCalibrationManager:
    def _manager(self, tmp_path) -> CalibrationManager:
        return CalibrationManager(CalibrationStore(tmp_path / "test.db"))

    def _delta(self, map_name: str = "injection_quantity_base") -> MapDelta:
        return MapDelta(map_name, "desc", "unit", [10.0], [11.0])

    def test_create_proposal_no_legal(self, tmp_path):
        mgr = self._manager(tmp_path)
        p = mgr.create_proposal(
            "bosch_me9", "Golf TDI", [self._delta()],
            "Mais torque", "Datalog bancada",
        )
        assert p.id
        assert p.guardian_level == 2
        assert p.requires_legal_note is False
        assert p.status == ProposalStatus.PENDING

    def test_create_emission_requires_legal_note(self, tmp_path):
        mgr = self._manager(tmp_path)
        with pytest.raises(CalibrationError, match="legal"):
            mgr.create_proposal(
                "bosch_edc16", "Audi A3", [self._delta("egr_rate_setpoint")],
                "Remoção EGR", "Bancada", legal_note="",
            )

    def test_create_emission_with_legal_note_ok(self, tmp_path):
        mgr = self._manager(tmp_path)
        p = mgr.create_proposal(
            "bosch_edc16", "Audi A3", [self._delta("egr_rate_setpoint")],
            "Remoção EGR", "Bancada",
            legal_note="Autorizado pelo proprietário Felipe.",
        )
        assert p.guardian_level == 4
        assert p.requires_legal_note is True

    def test_approve_proposal(self, tmp_path):
        mgr = self._manager(tmp_path)
        p = mgr.create_proposal("bosch_me9", "Golf", [self._delta()], "j", "v")
        approved = mgr.approve(p.id)
        assert approved.status == ProposalStatus.APPROVED
        assert approved.approved_by == "Felipe"

    def test_reject_proposal(self, tmp_path):
        mgr = self._manager(tmp_path)
        p = mgr.create_proposal("bosch_me9", "Golf", [self._delta()], "j", "v")
        rejected = mgr.reject(p.id, "Risco alto sem datalog")
        assert rejected.status == ProposalStatus.REJECTED
        assert "datalog" in rejected.rejection_reason

    def test_mark_applied_requires_approved(self, tmp_path):
        mgr = self._manager(tmp_path)
        p = mgr.create_proposal("bosch_me9", "Golf", [self._delta()], "j", "v")
        with pytest.raises(CalibrationError, match="Só propostas aprovadas"):
            mgr.mark_applied(p.id)

    def test_approve_then_mark_applied(self, tmp_path):
        mgr = self._manager(tmp_path)
        p = mgr.create_proposal("bosch_me9", "Golf", [self._delta()], "j", "v")
        mgr.approve(p.id)
        applied = mgr.mark_applied(p.id)
        assert applied.status == ProposalStatus.APPLIED
        assert applied.applied_at > 0

    def test_context_for_ecu_known(self, tmp_path):
        mgr = self._manager(tmp_path)
        ctx = mgr.context_for_ecu("bosch_me9")
        assert "Bosch" in ctx

    def test_find_family(self, tmp_path):
        mgr = self._manager(tmp_path)
        f = mgr.find_family("bosch")
        assert f is not None

    def test_all_maps(self, tmp_path):
        mgr = self._manager(tmp_path)
        maps = mgr.all_maps()
        assert len(maps) >= 10
