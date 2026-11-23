"""
Testes unitários — Fase 5: Firmware e protocolos.
Todos com dados sintéticos — nunca firmware real de cliente.
"""
import pytest

from src.firmware.protocols import (
    ProtocolSpec, ProtocolLayer, ServiceID,
    get_protocol, list_protocols,
)
from src.firmware.bootloader import (
    BootloaderProfile, BootMode,
    get_profile, list_profiles, profiles_for_family,
)
from src.firmware.interfaces import (
    FlashInterfaces, InterfaceStatus, ReadResult, WriteResult,
)


# ── Protocols ─────────────────────────────────────────────────────────────────

class TestProtocols:
    def test_list_protocols_not_empty(self):
        assert len(list_protocols()) >= 4

    def test_get_uds_protocol(self):
        p = get_protocol("UDS")
        assert p is not None
        assert p.standard == "ISO 14229"
        assert p.layer == ProtocolLayer.SESSION

    def test_get_kwp2000(self):
        p = get_protocol("KWP2000")
        assert p is not None
        assert "ISO 14230" in p.standard

    def test_get_can_protocol(self):
        p = get_protocol("CAN")
        assert p is not None
        assert p.layer == ProtocolLayer.DATALINK

    def test_get_kline_protocol(self):
        p = get_protocol("K-Line")
        assert p is not None
        assert p.layer == ProtocolLayer.PHYSICAL

    def test_get_obd2_protocol(self):
        p = get_protocol("OBD-II")
        assert p is not None
        assert len(p.services) >= 4

    def test_uds_has_key_services(self):
        p = get_protocol("UDS")
        sids = {s.sid for s in p.services}
        assert 0x10 in sids  # DiagnosticSessionControl
        assert 0x27 in sids  # SecurityAccess
        assert 0x34 in sids  # RequestDownload
        assert 0x3E in sids  # TesterPresent

    def test_get_missing_returns_none(self):
        assert get_protocol("PROTOCOLO_INEXISTENTE") is None

    def test_protocol_summary(self):
        p = get_protocol("UDS")
        s = p.summary()
        assert "UDS" in s
        assert "ISO 14229" in s

    def test_uds_baud_rates(self):
        p = get_protocol("UDS")
        assert 500000 in p.typical_baud

    def test_kline_baud_rate(self):
        p = get_protocol("K-Line")
        assert 10400 in p.typical_baud


# ── BootloaderProfiles ────────────────────────────────────────────────────────

class TestBootloaderProfiles:
    def test_list_profiles_not_empty(self):
        assert len(list_profiles()) >= 3

    def test_get_bosch_me9_bsl(self):
        p = get_profile("bosch_me9_bsl")
        assert p is not None
        assert p.manufacturer == "Bosch"
        assert BootMode.BSL in p.modes

    def test_get_bosch_med17_bsl(self):
        p = get_profile("bosch_med17_bsl")
        assert p is not None
        assert BootMode.BOOT_CAN in p.modes

    def test_delphi_obd(self):
        p = get_profile("delphi_mt20u2_obd")
        assert p is not None
        assert BootMode.OBD in p.modes
        assert p.obd_session_id == 0x92

    def test_denso_requires_bench(self):
        p = get_profile("denso_sh7xxx_kline")
        assert p is not None
        assert p.requires_bench is True

    def test_profiles_for_family_bosch(self):
        profiles = profiles_for_family("bosch_me9")
        assert len(profiles) >= 1
        assert any("bosch" in p.id for p in profiles)

    def test_get_missing_returns_none(self):
        assert get_profile("perfil_inexistente") is None

    def test_profile_summary(self):
        p = get_profile("bosch_me9_bsl")
        s = p.summary()
        assert "Bosch" in s
        assert "bsl" in s.lower() or "BSL" in s

    def test_erase_and_flash_times_positive(self):
        for p in list_profiles():
            assert p.typical_erase_time_s > 0
            assert p.typical_flash_time_s > 0


# ── FlashInterfaces ───────────────────────────────────────────────────────────

class TestFlashInterfaces:
    def test_sm2_not_available(self):
        fi = FlashInterfaces()
        assert fi.sm2.is_available() is False

    def test_sm2_status_disconnected(self):
        fi = FlashInterfaces()
        assert fi.sm2.status() == InterfaceStatus.DISCONNECTED

    def test_sm2_read_returns_error(self):
        fi = FlashInterfaces()
        result = fi.sm2.read(0x0000, 1024)
        assert result.success is False
        assert result.error != ""

    def test_sm2_write_returns_error(self):
        fi = FlashInterfaces()
        result = fi.sm2.write(0x0000, b"\x00" * 64, "proposal-id-fake")
        assert result.success is False
        assert result.error != ""

    def test_bdm_not_available(self):
        fi = FlashInterfaces()
        assert fi.bdm.is_available() is False

    def test_bdm_read_returns_error(self):
        fi = FlashInterfaces()
        result = fi.bdm.read(0x0000, 64)
        assert result.success is False

    def test_status_dict_keys(self):
        fi = FlashInterfaces()
        s = fi.status()
        assert "sm2" in s
        assert "bdm" in s
        assert "available" in s["sm2"]
        assert "status" in s["sm2"]

    def test_sm2_name(self):
        fi = FlashInterfaces()
        assert "SM2" in fi.sm2.interface_name()
