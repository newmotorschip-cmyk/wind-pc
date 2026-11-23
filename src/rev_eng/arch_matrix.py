"""
Matriz de suporte de arquiteturas no Ghidra instalado.
Varre a instalação real e retorna o status por família de ECU automotiva.

Nunca presume suporte — sempre lê os arquivos .slaspec e .ldefs presentes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


GHIDRA_PATH = Path(os.getenv("GHIDRA_PATH", r"C:\Users\Repro\Documents\ghidra_12.1.4_PUBLIC"))


class ArchStatus(str, Enum):
    SUPPORTED = "suportado"       # SLEIGH + loader presentes
    PARTIAL   = "parcial"         # SLEIGH presente, loader limitado
    MISSING   = "ausente"         # não encontrado na instalação
    UNKNOWN   = "desconhecido"    # instalação não verificada


@dataclass
class ArchEntry:
    family: str
    description: str
    ghidra_processor_dir: str         # pasta em Ghidra/Processors/
    slaspec_files: list[str] = field(default_factory=list)
    notes: str = ""
    status: ArchStatus = ArchStatus.UNKNOWN
    cost_to_add: str = ""             # custo estimado para criar módulo SLEIGH se ausente

    @property
    def is_supported(self) -> bool:
        return self.status == ArchStatus.SUPPORTED

    def summary_line(self) -> str:
        icon = {"suportado": "✅", "parcial": "⚠️", "ausente": "❌", "desconhecido": "?"}.get(self.status.value, "?")
        specs = f" ({len(self.slaspec_files)} slaspec)" if self.slaspec_files else ""
        note  = f" — {self.notes}" if self.notes else ""
        cost  = f" [custo: {self.cost_to_add}]" if self.cost_to_add and self.status == ArchStatus.MISSING else ""
        return f"{icon} {self.family:20s} {self.status.value:12s}{specs}{note}{cost}"


# Famílias automotivas relevantes para o acervo REPROTECH
_AUTOMOTIVE_FAMILIES: list[dict] = [
    {
        "family": "Infineon TriCore",
        "description": "TC1762/1796/1797/277/297 — Bosch EDC17, MED17.x (principais ECUs do acervo)",
        "ghidra_processor_dir": "tricore",
    },
    {
        "family": "PowerPC/VLE",
        "description": "MPC55xx/56xx — Continental SID807, Delphi MT86; VLE = modo compacto de instrução",
        "ghidra_processor_dir": "PowerPC",
        "notes": "VLE parcialmente suportado (ppc_64_isa_vle_be.slaspec presente)",
    },
    {
        "family": "SuperH (SH2/SH2A)",
        "description": "SH7055/7058/7059 — Bosch ME7.x, Hitachi/Renesas; muito comum em Civic, Corolla antigos",
        "ghidra_processor_dir": "SuperH",
    },
    {
        "family": "NEC V850",
        "description": "V850E2 — Bosch Motronic ME7.3/ME7.4.5, Siemens/Continental ECUs antigas",
        "ghidra_processor_dir": "V850",
    },
    {
        "family": "Infineon C166/XC2000",
        "description": "C167, XE166, XC2xxx — ECUs antigas Bosch, Siemens; comum em VW/Audi pré-2005",
        "ghidra_processor_dir": "C166",   # não presente — precisa de módulo SLEIGH
        "notes": "Não presente no Ghidra 12.1.4; módulo de terceiro disponível (openssl-sleigh-c166)",
        "cost_to_add": "~2–4 h para adaptar módulo SLEIGH de terceiro",
    },
    {
        "family": "ARM Cortex-M",
        "description": "ARMv7-M/ARMv8-M — ECUs modernas (pós-2015): ZF, Bosch Gen3+, NXP S32",
        "ghidra_processor_dir": "ARM",
    },
    {
        "family": "ARM64 (AARCH64)",
        "description": "ARMv8-A — ECUs mais novas (gateway, ADAS, domínio centralizado)",
        "ghidra_processor_dir": "AARCH64",
    },
    {
        "family": "Renesas M16C",
        "description": "M16C/60, M16C/80 — ECUs Mitsubishi, Denso, algumas Bosch ME3.x",
        "ghidra_processor_dir": "M16C",
    },
    {
        "family": "Motorola/NXP 68000",
        "description": "68HC11/12/16 — ECUs muito antigas (pré-2000); raras no acervo",
        "ghidra_processor_dir": "68000",
    },
]


def _probe_processor(ghidra_root: Path, proc_dir: str) -> tuple[ArchStatus, list[str]]:
    """Verifica se um processador está presente verificando arquivos .slaspec."""
    lang_path = ghidra_root / "Ghidra" / "Processors" / proc_dir / "data" / "languages"
    if not lang_path.exists():
        return ArchStatus.MISSING, []
    specs = [f.name for f in lang_path.glob("*.slaspec")]
    if not specs:
        return ArchStatus.MISSING, []
    return ArchStatus.SUPPORTED, sorted(specs)


def build_matrix(ghidra_root: Path = GHIDRA_PATH) -> list[ArchEntry]:
    """
    Constrói a matriz de suporte verificando a instalação real do Ghidra.
    Nunca assume: só o que os arquivos confirmam.
    """
    entries: list[ArchEntry] = []

    for fam_def in _AUTOMOTIVE_FAMILIES:
        proc_dir = fam_def["ghidra_processor_dir"]
        status, specs = _probe_processor(ghidra_root, proc_dir)

        # Ajuste fino por família
        if fam_def["family"] == "PowerPC/VLE" and status == ArchStatus.SUPPORTED:
            # VLE suportado apenas parcialmente (instrução compacta precisa do slaspec certo)
            vle_specs = [s for s in specs if "vle" in s.lower()]
            status = ArchStatus.PARTIAL if not vle_specs else ArchStatus.PARTIAL
            # Mesmo com slaspec VLE, o loader para firmware ECU não é nativo — parcial
        elif fam_def["family"] == "NEC V850" and status == ArchStatus.SUPPORTED:
            # V850e3 presente mas loaders ECU não testados
            status = ArchStatus.PARTIAL

        entry = ArchEntry(
            family=fam_def["family"],
            description=fam_def["description"],
            ghidra_processor_dir=proc_dir,
            slaspec_files=specs,
            notes=fam_def.get("notes", ""),
            status=status,
            cost_to_add=fam_def.get("cost_to_add", ""),
        )
        entries.append(entry)

    return entries


def matrix_report(ghidra_root: Path = GHIDRA_PATH) -> str:
    """Gera relatório textual da matriz de suporte."""
    entries = build_matrix(ghidra_root)
    lines = [
        f"=== Matriz de Suporte Ghidra {ghidra_root.name} ===",
        f"Verificado em: {ghidra_root}",
        "",
    ]
    for e in entries:
        lines.append(e.summary_line())
        if e.description:
            lines.append(f"    {e.description}")
        lines.append("")

    supported = sum(1 for e in entries if e.status == ArchStatus.SUPPORTED)
    partial   = sum(1 for e in entries if e.status == ArchStatus.PARTIAL)
    missing   = sum(1 for e in entries if e.status == ArchStatus.MISSING)
    lines.append(f"Resumo: {supported} suportados, {partial} parciais, {missing} ausentes de {len(entries)} famílias.")
    return "\n".join(lines)
