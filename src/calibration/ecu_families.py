"""
Base de conhecimento de famílias de ECU automotivas.
Dados técnicos verificados ou explicitamente marcados como hipótese.
Nunca presumir suporte — listar somente o que está documentado.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EcuFamily:
    id: str
    manufacturer: str
    series: str
    description: str
    architectures: list[str]
    common_formats: list[str]
    checksum_algorithm: str
    notes: str
    typical_flash_size_kb: int = 0
    typical_ram_kb: int = 0
    boot_modes: list[str] = field(default_factory=list)

    def summary_line(self) -> str:
        return f"{self.manufacturer} {self.series} — {self.description} ({'/'.join(self.architectures)})"


_KNOWN_FAMILIES: list[EcuFamily] = [
    EcuFamily(
        id="bosch_me9",
        manufacturer="Bosch",
        series="ME 9.x",
        description="Gestão motor gasolina com VVT — europeus 2003–2010",
        architectures=["TriCore TC1762", "TC1796"],
        common_formats=["A2L", "ODX"],
        checksum_algorithm="crc32_bosch_me9",
        typical_flash_size_kb=1024,
        typical_ram_kb=96,
        boot_modes=["OBD", "BDM", "BSL"],
        notes="Checksum em offset fixo; proteção de leitura via lock bits TC1796.",
    ),
    EcuFamily(
        id="bosch_med17",
        manufacturer="Bosch",
        series="MED 17.x",
        description="Gestão motor gasolina injeção direta — 2008+",
        architectures=["TriCore TC1766", "TC1797", "TC1793"],
        common_formats=["A2L", "ODX", "DAMOS"],
        checksum_algorithm="crc32_bosch_med17",
        typical_flash_size_kb=4096,
        typical_ram_kb=512,
        boot_modes=["OBD KWP2000", "OBD UDS", "BDM", "BSL", "Boot mode CAN"],
        notes="Família mais usada em VW/Audi/BMW. CRC calculado sobre múltiplos blocos.",
    ),
    EcuFamily(
        id="bosch_edc16",
        manufacturer="Bosch",
        series="EDC 16",
        description="Gestão motor diesel common rail — 2003–2010",
        architectures=["TriCore TC1762", "TC1796"],
        common_formats=["A2L", "DAMOS", "ODX"],
        checksum_algorithm="crc16_bosch_edc16",
        typical_flash_size_kb=1024,
        typical_ram_kb=96,
        boot_modes=["OBD KWP2000", "CAN", "BDM"],
        notes="Muito comum em VW/Audi/Seat/Skoda diesel 1.9/2.0 TDI.",
    ),
    EcuFamily(
        id="bosch_edc17",
        manufacturer="Bosch",
        series="EDC 17.x",
        description="Gestão motor diesel common rail de nova geração — 2008+",
        architectures=["TriCore TC1766", "TC1797"],
        common_formats=["A2L", "ODX", "DAMOS"],
        checksum_algorithm="crc32_bosch_edc17",
        typical_flash_size_kb=4096,
        typical_ram_kb=512,
        boot_modes=["OBD UDS", "BDM", "BSL", "Boot mode CAN"],
        notes="Successor do EDC16, presente em BMW/Mercedes/VW/PSA diesel.",
    ),
    EcuFamily(
        id="continental_sid208",
        manufacturer="Continental",
        series="SID 208",
        description="ECU diesel PSA/Ford — 2.0 HDi, 1.6 TDCi",
        architectures=["PowerPC MPC563", "MPC5566"],
        common_formats=["A2L", "ODX"],
        checksum_algorithm="crc32_continental",
        typical_flash_size_kb=2048,
        typical_ram_kb=256,
        boot_modes=["OBD KWP2000", "K-Line", "CAN"],
        notes="PowerPC big-endian. Hipótese: baseado em MPC56x (não verificado em hardware).",
    ),
    EcuFamily(
        id="continental_pcr2_1",
        manufacturer="Continental",
        series="PCR 2.1",
        description="ECU motor gasolina PSA/GM — 1.4/1.6 Flex (Brasil)",
        architectures=["PowerPC MPC5566"],
        common_formats=["A2L"],
        checksum_algorithm="crc32_continental",
        typical_flash_size_kb=2048,
        typical_ram_kb=256,
        boot_modes=["OBD KWP2000", "CAN"],
        notes="Muito presente no mercado brasileiro (Corsa, Vectra, Zafira, C3).",
    ),
    EcuFamily(
        id="delphi_mt20u2",
        manufacturer="Delphi",
        series="MT20U2",
        description="Gestão motor gasolina — mercado emergente, muito comum no Brasil",
        architectures=["Motorola HCS12 / S12X"],
        common_formats=["A2L", "hex"],
        checksum_algorithm="checksum8_sum",
        typical_flash_size_kb=256,
        typical_ram_kb=16,
        boot_modes=["OBD KWP2000", "K-Line", "CAN"],
        notes="Muito usado em Chevrolet/GM Brasil (Celta, Classic, Prisma, Cobalt).",
    ),
    EcuFamily(
        id="denso_sh7xxx",
        manufacturer="Denso",
        series="SH7xxx",
        description="ECU motor gasolina/diesel Toyota/Subaru/Mitsubishi",
        architectures=["SuperH SH7055", "SH7058", "SH7059"],
        common_formats=["A2L", "hex", "BIN"],
        checksum_algorithm="checksum16_denso",
        typical_flash_size_kb=512,
        typical_ram_kb=64,
        boot_modes=["OBD KWP2000", "K-Line", "BOOT"],
        notes="SuperH big-endian. Hipótese: SH7055 no Corolla/Camry; SH7058/59 em esportivos.",
    ),
    EcuFamily(
        id="marelli_iaw5nf",
        manufacturer="Marelli",
        series="IAW 5NF/5SF",
        description="Gestão motor gasolina — Fiat/Alfa Romeo (Brasil muito comum)",
        architectures=["Motorola MPC561", "MPC562"],
        common_formats=["A2L", "hex"],
        checksum_algorithm="checksum_marelli",
        typical_flash_size_kb=512,
        typical_ram_kb=64,
        boot_modes=["OBD KWP2000", "K-Line"],
        notes="Muito comum em Fiat Palio/Uno/Siena. MPC56x PowerPC.",
    ),
]

_FAMILY_INDEX: dict[str, EcuFamily] = {f.id: f for f in _KNOWN_FAMILIES}


def get_family(family_id: str) -> Optional[EcuFamily]:
    return _FAMILY_INDEX.get(family_id)


def list_families() -> list[EcuFamily]:
    return list(_KNOWN_FAMILIES)


def search_families(query: str) -> list[EcuFamily]:
    q = query.lower()
    return [f for f in _KNOWN_FAMILIES
            if q in f.manufacturer.lower()
            or q in f.series.lower()
            or q in f.description.lower()
            or q in " ".join(f.architectures).lower()
            or q in f.id.lower()]
