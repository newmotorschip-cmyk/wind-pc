"""
Pipeline de engenharia reversa da WIND.
Fluxo: preservar → identificar formato/arq. → importar Ghidra → analisar → relatório.
Nunca modifica o original. Sempre trabalha em cópia verificada por hash.
"""
from __future__ import annotations

import os
import struct
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .arch_matrix import ArchStatus, build_matrix, GHIDRA_PATH
from .file_guard import FileGuard, FileRecord
from .ghidra_client import GhidraClient, GhidraResult


WORK_ROOT = Path(os.getenv("WIND_RE_WORKDIR", "data/re_workspace"))


class BinaryFormat(str, Enum):
    MOTOROLA_SREC = "motorola_srec"   # S-record (.s19/.s28/.s37)
    INTEL_HEX     = "intel_hex"       # Intel HEX (.hex/.ihx)
    BINARY_RAW    = "binary_raw"      # dump binário puro (.bin)
    ELF           = "elf"             # ELF (Linux toolchains)
    PE            = "pe"              # PE/COFF (raro em ECUs)
    UNKNOWN       = "unknown"


class IdentifiedArch(str, Enum):
    TRICORE    = "tricore"
    POWERPC    = "powerpc"
    SUPERH     = "superh"
    V850       = "v850"
    ARM        = "arm"
    AARCH64    = "aarch64"
    M16C       = "m16c"
    C166       = "c166"
    X86        = "x86"
    UNKNOWN    = "unknown"


# Mapeamento arch → Ghidra language ID
ARCH_TO_LANGUAGE: dict[IdentifiedArch, str] = {
    IdentifiedArch.TRICORE: "tricore:LE:32:default",
    IdentifiedArch.POWERPC: "PowerPC:BE:32:default",
    IdentifiedArch.SUPERH:  "SuperH:BE:32:SH-2A",
    IdentifiedArch.V850:    "V850:LE:32:default",
    IdentifiedArch.ARM:     "ARM:LE:32:v7",
    IdentifiedArch.AARCH64: "AARCH64:LE:64:v8A",
    IdentifiedArch.M16C:    "M16C:BE:32:M16C_80",
    IdentifiedArch.X86:     "x86:LE:32:default",
}


@dataclass
class PipelineReport:
    job_id: str
    original_path: str
    sha256: str
    size_bytes: int
    detected_format: BinaryFormat
    detected_arch: IdentifiedArch
    arch_confidence: str              # "high" | "medium" | "low" | "none"
    ghidra_available: bool
    ghidra_result: Optional[GhidraResult]
    findings: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    created_at: float = field(default_factory=time.time)

    def summary(self) -> str:
        lines = [
            f"=== Relatório RE — Job {self.job_id[:8]} ===",
            f"Arquivo:  {Path(self.original_path).name}",
            f"SHA-256:  {self.sha256[:32]}...",
            f"Tamanho:  {self.size_bytes:,} bytes ({self.size_bytes/1024:.1f} KB)",
            f"Formato:  {self.detected_format.value}",
            f"Arq.:     {self.detected_arch.value} (confiança: {self.arch_confidence})",
            f"Ghidra:   {'disponível' if self.ghidra_available else 'não disponível'}",
        ]
        if self.ghidra_result:
            lines.append(f"Análise:  {'OK' if self.ghidra_result.success else 'falhou — ' + (self.ghidra_result.error or '')}")
        if self.findings:
            lines.append("\nAchados:")
            for f in self.findings:
                lines.append(f"  · {f}")
        if self.hypotheses:
            lines.append("\nHipóteses [NÃO VALIDADAS]:")
            for h in self.hypotheses:
                lines.append(f"  ? {h}")
        if self.warnings:
            lines.append("\nAvisos:")
            for w in self.warnings:
                lines.append(f"  ⚠ {w}")
        lines.append(f"\nDuração: {self.duration_s:.1f}s")
        return "\n".join(lines)


def _detect_format(data: bytes) -> BinaryFormat:
    """Detecta o formato do arquivo pelo magic/cabeçalho."""
    if not data:
        return BinaryFormat.UNKNOWN
    # S-record: começa com S0, S1, S2, S3
    if data[:2] in (b"S0", b"S1", b"S2", b"S3"):
        return BinaryFormat.MOTOROLA_SREC
    if data[0:1] in (b"S",) and chr(data[1]) in "0123":
        return BinaryFormat.MOTOROLA_SREC
    # Intel HEX: começa com ':'
    if data[0:1] == b":":
        return BinaryFormat.INTEL_HEX
    # ELF magic
    if data[:4] == b"\x7fELF":
        return BinaryFormat.ELF
    # PE/MZ
    if data[:2] == b"MZ":
        return BinaryFormat.PE
    # Padrão: binário raw
    return BinaryFormat.BINARY_RAW


def _detect_arch_heuristic(data: bytes, fmt: BinaryFormat) -> tuple[IdentifiedArch, str]:
    """
    Heurística de identificação de arquitetura por padrões de instrução.
    Retorna (arch, confidence). Nunca garante — só hipótese inicial.
    """
    if len(data) < 64:
        return IdentifiedArch.UNKNOWN, "none"

    sample = data[:min(len(data), 65536)]

    # TriCore: magic word 0x00000000 no vetor reset, padrão de opcode MOV16
    tricore_opcodes = sum(1 for i in range(0, len(sample)-1, 2)
                         if sample[i] & 0x0F in (0x06, 0x0A, 0x2E, 0x82))
    if tricore_opcodes > len(sample) // 20:
        return IdentifiedArch.TRICORE, "medium"

    # PowerPC/VLE: opcodes BE com primeiros 6 bits típicos
    if len(sample) >= 4:
        word = struct.unpack(">I", sample[:4])[0]
        ppc_primary = (word >> 26) & 0x3F
        if ppc_primary in (18, 16, 14, 15, 24, 25, 28, 29):
            return IdentifiedArch.POWERPC, "medium"

    # SuperH: instruções de 16 bits, padrões de opcode SH2
    sh_load_ops = sum(1 for i in range(0, len(sample)-1, 2)
                      if (sample[i] & 0xF0) == 0x60)
    if sh_load_ops > len(sample) // 50:
        return IdentifiedArch.SUPERH, "low"

    # ARM Thumb: BX LR pattern ou NOP Thumb
    if b"\x70\x47" in sample[:4096] or b"\x00\xBF" in sample[:4096]:
        return IdentifiedArch.ARM, "medium"

    return IdentifiedArch.UNKNOWN, "none"


class REPipeline:
    """
    Pipeline completo de engenharia reversa.
    1. Preservar original (hash + cópia read-only)
    2. Identificar formato e arquitetura
    3. Importar no Ghidra (headless)
    4. Extrair achados
    5. Gerar relatório
    """

    def __init__(
        self,
        ghidra_root: Path = GHIDRA_PATH,
        work_root: Path = WORK_ROOT,
    ) -> None:
        self._guard  = FileGuard(work_root)
        self._client = GhidraClient(ghidra_root, work_root)
        self._matrix = build_matrix(ghidra_root)

    def run(
        self,
        source_path: str | Path,
        force_arch: Optional[IdentifiedArch] = None,
        run_ghidra: bool = True,
    ) -> PipelineReport:
        """
        Executa o pipeline completo.
        force_arch: sobrepõe a detecção automática.
        run_ghidra: False para apenas identificar sem importar.
        """
        t0 = time.time()
        job_id = str(uuid.uuid4())[:12]
        warnings: list[str] = []
        findings: list[str] = []
        hypotheses: list[str] = []

        # 1. Preservar original
        try:
            record: FileRecord = self._guard.protect(source_path, job_id=job_id)
        except FileNotFoundError as e:
            return PipelineReport(
                job_id=job_id, original_path=str(source_path), sha256="", size_bytes=0,
                detected_format=BinaryFormat.UNKNOWN, detected_arch=IdentifiedArch.UNKNOWN,
                arch_confidence="none", ghidra_available=self._client.is_available,
                ghidra_result=None, warnings=[str(e)], duration_s=time.time()-t0,
            )

        # 2. Identificar formato e arquitetura
        data = record.verify() and Path(record.work_path).read_bytes() or b""
        fmt  = _detect_format(data)
        arch, confidence = _detect_arch_heuristic(data, fmt)

        if force_arch:
            arch = force_arch
            confidence = "manual"
            findings.append(f"Arquitetura definida manualmente: {arch.value}")
        else:
            if arch == IdentifiedArch.UNKNOWN:
                warnings.append("Arquitetura não identificada automaticamente. Use force_arch=.")
            else:
                hypotheses.append(f"Arquitetura detectada como {arch.value} (confiança: {confidence}) — hipótese, não validado.")

        # 3. Verificar suporte no Ghidra
        arch_support = {e.ghidra_processor_dir.lower(): e for e in self._matrix}
        arch_map = {
            IdentifiedArch.TRICORE: "tricore",
            IdentifiedArch.POWERPC: "powerpc",
            IdentifiedArch.SUPERH: "superh",
            IdentifiedArch.V850: "v850",
            IdentifiedArch.ARM: "arm",
            IdentifiedArch.AARCH64: "aarch64",
            IdentifiedArch.M16C: "m16c",
        }
        if arch != IdentifiedArch.UNKNOWN:
            proc_key = arch_map.get(arch, "")
            entry = next((e for e in self._matrix if e.ghidra_processor_dir.lower() == proc_key), None)
            if entry and entry.status == ArchStatus.MISSING:
                warnings.append(f"Processador {arch.value} não presente no Ghidra. {entry.cost_to_add}")
            elif entry and entry.status == ArchStatus.PARTIAL:
                warnings.append(f"Suporte parcial para {arch.value} no Ghidra.")

        # 4. Importar no Ghidra (somente se disponível e solicitado)
        ghidra_result: Optional[GhidraResult] = None
        if run_ghidra and self._client.is_available and arch != IdentifiedArch.UNKNOWN:
            lang_id = ARCH_TO_LANGUAGE.get(arch, "")
            if lang_id:
                ghidra_result = self._client.analyze(
                    record.work_path, job_id=job_id, language_id=lang_id
                )
                if ghidra_result.success:
                    findings.append(f"Análise Ghidra concluída em {ghidra_result.duration_s:.1f}s")
                else:
                    warnings.append(f"Ghidra falhou: {ghidra_result.error}")
            else:
                warnings.append(f"Nenhum language_id mapeado para {arch.value}")
        elif not self._client.is_available:
            warnings.append("analyzeHeadless não encontrado. Análise Ghidra pulada.")

        # 5. Achados básicos do arquivo
        findings.append(f"Formato detectado: {fmt.value}")
        findings.append(f"Tamanho: {record.size_bytes:,} bytes")
        findings.append(f"SHA-256: {record.sha256}")

        return PipelineReport(
            job_id=job_id,
            original_path=record.original_path,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
            detected_format=fmt,
            detected_arch=arch,
            arch_confidence=confidence,
            ghidra_available=self._client.is_available,
            ghidra_result=ghidra_result,
            findings=findings,
            hypotheses=hypotheses,
            warnings=warnings,
            duration_s=time.time() - t0,
        )
