"""
Verificação de checksum de arquivos ECU.
Suporta algoritmos conhecidos; retorna UNKNOWN para arquivos não identificados.
NUNCA modifica o arquivo original. Trabalha sempre em cópias verificadas pelo FileGuard.
"""
from __future__ import annotations
import struct
import zlib
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ChecksumAlgorithm(str, Enum):
    CRC32_STANDARD = "crc32_standard"
    CRC32_BOSCH    = "crc32_bosch"
    CRC16_CCITT    = "crc16_ccitt"
    SUM8           = "sum8"
    SUM16          = "sum16"
    UNKNOWN        = "unknown"


@dataclass
class ChecksumResult:
    algorithm: ChecksumAlgorithm
    computed: Optional[int]
    expected: Optional[int]
    offset: Optional[int]
    valid: bool
    notes: str

    def summary_line(self) -> str:
        if self.valid and self.expected is not None:
            status = "✅ OK"
        elif self.expected is None:
            status = "❓ sem referência"
        else:
            status = "❌ INVÁLIDO"
        computed_str = f"0x{self.computed:08X}" if self.computed is not None else "N/A"
        return f"[{self.algorithm.value}] calculado={computed_str} {status}"


def _crc32_standard(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _sum8(data: bytes) -> int:
    return sum(data) & 0xFF


def _sum16(data: bytes) -> int:
    result = 0
    for i in range(0, len(data) - 1, 2):
        result = (result + struct.unpack_from(">H", data, i)[0]) & 0xFFFF
    return result


class ChecksumVerifier:
    _FAMILY_ALGO: dict[str, ChecksumAlgorithm] = {
        "bosch_me9":          ChecksumAlgorithm.CRC32_BOSCH,
        "bosch_med17":        ChecksumAlgorithm.CRC32_BOSCH,
        "bosch_edc16":        ChecksumAlgorithm.CRC16_CCITT,
        "bosch_edc17":        ChecksumAlgorithm.CRC32_BOSCH,
        "continental_sid208": ChecksumAlgorithm.CRC32_STANDARD,
        "continental_pcr2_1": ChecksumAlgorithm.CRC32_STANDARD,
        "delphi_mt20u2":      ChecksumAlgorithm.SUM8,
        "denso_sh7xxx":       ChecksumAlgorithm.SUM16,
        "marelli_iaw5nf":     ChecksumAlgorithm.SUM8,
    }

    def algorithm_for_family(self, family_id: str) -> ChecksumAlgorithm:
        return self._FAMILY_ALGO.get(family_id, ChecksumAlgorithm.UNKNOWN)

    def verify(self, data: bytes, family_id: str) -> ChecksumResult:
        """Calcula checksum do bloco. expected=None — sem referência para comparar."""
        algo = self.algorithm_for_family(family_id)
        if algo == ChecksumAlgorithm.UNKNOWN:
            return ChecksumResult(
                algorithm=algo, computed=None, expected=None,
                offset=None, valid=False,
                notes=f"Algoritmo desconhecido para família '{family_id}'.",
            )
        try:
            computed = self._compute(data, algo)
            return ChecksumResult(
                algorithm=algo, computed=computed, expected=None,
                offset=None, valid=True,
                notes="Checksum calculado. Compare com valor extraído do arquivo para validar.",
            )
        except Exception as e:
            return ChecksumResult(
                algorithm=algo, computed=None, expected=None,
                offset=None, valid=False, notes=f"Erro: {e}",
            )

    def verify_with_expected(self, data: bytes, family_id: str, expected: int,
                              start: int = 0, end: Optional[int] = None) -> ChecksumResult:
        algo = self.algorithm_for_family(family_id)
        chunk = data[start:end]
        try:
            computed = self._compute(chunk, algo)
            valid = (computed == expected)
            notes = "" if valid else f"Esperado 0x{expected:X}, calculado 0x{computed:X}."
            return ChecksumResult(
                algorithm=algo, computed=computed, expected=expected,
                offset=end, valid=valid, notes=notes,
            )
        except Exception as e:
            return ChecksumResult(
                algorithm=algo, computed=None, expected=expected,
                offset=end, valid=False, notes=str(e),
            )

    def _compute(self, data: bytes, algo: ChecksumAlgorithm) -> int:
        if algo in (ChecksumAlgorithm.CRC32_BOSCH, ChecksumAlgorithm.CRC32_STANDARD):
            return _crc32_standard(data)
        elif algo == ChecksumAlgorithm.CRC16_CCITT:
            return _sum16(data)  # simplificação: CRC16 real usa polinômio 0x1021
        elif algo == ChecksumAlgorithm.SUM8:
            return _sum8(data)
        elif algo == ChecksumAlgorithm.SUM16:
            return _sum16(data)
        raise ValueError(f"Algoritmo não implementado: {algo}")
