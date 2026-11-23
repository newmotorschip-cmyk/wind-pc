"""
Perfis de bootloader conhecidos em ECUs automotivas.
Usado para identificar o modo de programação disponível antes de tentar gravação.
Dados de documentação pública e engenharia reversa aberta.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BootMode(str, Enum):
    OBD       = "obd"
    BDM       = "bdm"
    BSL       = "bsl"
    BOOT_CAN  = "boot_can"
    BOOT_KLINE = "boot_kline"
    BENCH     = "bench"
    JTAG      = "jtag"


@dataclass
class BootloaderProfile:
    id: str
    description: str
    manufacturer: str
    architecture: str
    modes: list[BootMode]
    obd_session_id: Optional[int]
    seed_key_level: Optional[int]
    typical_erase_time_s: float
    typical_flash_time_s: float
    notes: str
    requires_bench: bool = False

    def summary(self) -> str:
        modes_str = "/".join(m.value for m in self.modes)
        return f"{self.manufacturer} — {self.description} [{modes_str}]"


BOOTLOADER_PROFILES: list[BootloaderProfile] = [
    BootloaderProfile(
        id="bosch_me9_bsl",
        description="Bootstrap Loader do TriCore TC1762/TC1796",
        manufacturer="Bosch",
        architecture="TriCore",
        modes=[BootMode.BSL, BootMode.OBD, BootMode.BDM],
        obd_session_id=0x02,
        seed_key_level=0x01,
        typical_erase_time_s=15.0,
        typical_flash_time_s=30.0,
        notes=(
            "BSL via UART: jumper no pino BSL do TriCore. BDM via conector 10 pinos. "
            "OBD via KWP2000 fast init. Lock bits desativam BDM em produção."
        ),
    ),
    BootloaderProfile(
        id="bosch_med17_bsl",
        description="Bootstrap Loader do TriCore TC1766/TC1797",
        manufacturer="Bosch",
        architecture="TriCore",
        modes=[BootMode.BSL, BootMode.OBD, BootMode.BDM, BootMode.BOOT_CAN],
        obd_session_id=0x02,
        seed_key_level=0x01,
        typical_erase_time_s=20.0,
        typical_flash_time_s=45.0,
        notes=(
            "BSL pin na placa; CAN boot via mensagem de autenticação proprietária. "
            "MED17.9: OBD UDS. MED17.5.5: CAN boot sem BSL físico."
        ),
    ),
    BootloaderProfile(
        id="delphi_mt20u2_obd",
        description="OBD KWP2000 — HCS12 / S12X",
        manufacturer="Delphi",
        architecture="Motorola HCS12",
        modes=[BootMode.OBD, BootMode.BOOT_KLINE, BootMode.BENCH],
        obd_session_id=0x92,
        seed_key_level=0x01,
        typical_erase_time_s=5.0,
        typical_flash_time_s=15.0,
        notes=(
            "K-Line 10.4 kbps, fast init. Sessão 0x92 'diagnostic'. "
            "Seed/key de 2 bytes; algoritmo publicado em fóruns (invertXOR). "
            "Hipótese: bench sem ligação do fusível principal."
        ),
    ),
    BootloaderProfile(
        id="continental_sid208_can",
        description="CAN UDS programming — MPC563/5566",
        manufacturer="Continental",
        architecture="PowerPC",
        modes=[BootMode.OBD, BootMode.BOOT_CAN],
        obd_session_id=0x02,
        seed_key_level=0x11,
        typical_erase_time_s=25.0,
        typical_flash_time_s=50.0,
        notes="UDS 0x27 nível 0x11 para prog session. Hipótese: baseado em MPC56x (não verificado).",
    ),
    BootloaderProfile(
        id="denso_sh7xxx_kline",
        description="K-Line KWP2000 — SuperH SH7055/7058/7059",
        manufacturer="Denso",
        architecture="SuperH",
        modes=[BootMode.OBD, BootMode.BOOT_KLINE, BootMode.BENCH],
        obd_session_id=0x85,
        seed_key_level=0x01,
        typical_erase_time_s=8.0,
        typical_flash_time_s=20.0,
        requires_bench=True,
        notes=(
            "SH7055 e SH7058 no modo boot: RST low + MD0/MD1 pull. "
            "K-Line 15.625 kbps para upload. "
            "SH7059 (Subaru/Mitsubishi esportivos) exige seed/key específico."
        ),
    ),
]

_PROFILE_INDEX: dict[str, BootloaderProfile] = {p.id: p for p in BOOTLOADER_PROFILES}


def get_profile(profile_id: str) -> Optional[BootloaderProfile]:
    return _PROFILE_INDEX.get(profile_id)


def list_profiles() -> list[BootloaderProfile]:
    return BOOTLOADER_PROFILES


def profiles_for_family(family_id: str) -> list[BootloaderProfile]:
    fid = family_id.lower()
    return [p for p in BOOTLOADER_PROFILES if fid.split("_")[0] in p.id.lower()]
