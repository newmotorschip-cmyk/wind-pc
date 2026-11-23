"""
Testes unitários — Fase 4: RE (arch_matrix, file_guard, pipeline, repro_native).
Todos com dados sintéticos — nunca dados reais de cliente ou firmware real.
"""
import hashlib
import struct
import tempfile
from pathlib import Path

import pytest

from src.rev_eng.arch_matrix import ArchEntry, ArchStatus, build_matrix, matrix_report, GHIDRA_PATH
from src.rev_eng.file_guard import FileGuard, _sha256
from src.rev_eng.pipeline import (
    BinaryFormat as PFmt, IdentifiedArch, REPipeline, _detect_format, _detect_arch_heuristic,
)
from src.rev_eng.repro_native import DiffStub, DtcDetectorStub, ReproNativeConnectors


# ── Helpers ───────────────────────────────────────────────────────────────────

def _synthetic_bin(size: int = 1024, pattern: bytes = b"\xAA\xBB") -> bytes:
    """Binário sintético puro — sem dados reais de firmware."""
    return (pattern * (size // len(pattern) + 1))[:size]


def _srecord_header() -> bytes:
    return b"S00F000068656C6C6F202020202000003C\r\nS9030000FC\r\n"


def _intel_hex_simple() -> bytes:
    return b":10000000000102030405060708090A0B0C0D0E0F78\r\n:00000001FF\r\n"


# ── arch_matrix ───────────────────────────────────────────────────────────────

class TestArchMatrix:
    def test_matrix_runs_on_real_ghidra(self):
        """Verifica que a matriz é construída sem erros na instalação real."""
        matrix = build_matrix(GHIDRA_PATH)
        assert len(matrix) > 0

    def test_tricore_present(self):
        matrix = build_matrix(GHIDRA_PATH)
        tc = next((e for e in matrix if "TriCore" in e.family), None)
        assert tc is not None
        assert tc.status == ArchStatus.SUPPORTED
        assert any("tricore" in s.lower() for s in tc.slaspec_files)

    def test_powerpc_present(self):
        matrix = build_matrix(GHIDRA_PATH)
        ppc = next((e for e in matrix if "PowerPC" in e.family), None)
        assert ppc is not None
        assert ppc.status in (ArchStatus.SUPPORTED, ArchStatus.PARTIAL)

    def test_superh_present(self):
        matrix = build_matrix(GHIDRA_PATH)
        sh = next((e for e in matrix if "SuperH" in e.family), None)
        assert sh is not None
        assert sh.status in (ArchStatus.SUPPORTED, ArchStatus.PARTIAL)

    def test_v850_present(self):
        matrix = build_matrix(GHIDRA_PATH)
        v850 = next((e for e in matrix if "V850" in e.family), None)
        assert v850 is not None
        assert v850.status in (ArchStatus.SUPPORTED, ArchStatus.PARTIAL)

    def test_c166_missing(self):
        """C166/XC2000 não está no Ghidra 12.1.4 padrão."""
        matrix = build_matrix(GHIDRA_PATH)
        c166 = next((e for e in matrix if "C166" in e.family), None)
        assert c166 is not None
        assert c166.status == ArchStatus.MISSING

    def test_arm_present(self):
        matrix = build_matrix(GHIDRA_PATH)
        arm = next((e for e in matrix if e.family == "ARM Cortex-M"), None)
        assert arm is not None
        assert arm.status == ArchStatus.SUPPORTED

    def test_matrix_report_text(self):
        report = matrix_report(GHIDRA_PATH)
        assert "TriCore" in report
        assert "✅" in report or "❌" in report

    def test_arch_entry_summary_line(self):
        entry = ArchEntry(
            family="TestArch", description="Test", ghidra_processor_dir="test",
            slaspec_files=["test.slaspec"], status=ArchStatus.SUPPORTED,
        )
        line = entry.summary_line()
        assert "TestArch" in line
        assert "✅" in line


# ── file_guard ────────────────────────────────────────────────────────────────

class TestFileGuard:
    def test_protect_creates_work_copy(self, tmp_path):
        src = tmp_path / "firmware_synth.bin"
        src.write_bytes(_synthetic_bin())
        guard = FileGuard(tmp_path / "work")
        record = guard.protect(src, job_id="test001")
        assert Path(record.work_path).exists()
        assert record.sha256 == _sha256(src)

    def test_sidecar_hash_file_created(self, tmp_path):
        src = tmp_path / "fw.bin"
        src.write_bytes(_synthetic_bin())
        guard = FileGuard(tmp_path / "work")
        record = guard.protect(src, job_id="test002")
        sidecar = Path(record.work_path).with_suffix(".bin.sha256")
        assert sidecar.exists()
        assert record.sha256 in sidecar.read_text()

    def test_verify_integrity_ok(self, tmp_path):
        src = tmp_path / "fw.bin"
        src.write_bytes(_synthetic_bin())
        guard = FileGuard(tmp_path / "work")
        record = guard.protect(src, job_id="test003")
        assert record.verify()

    def test_verify_detects_tampering(self, tmp_path):
        src = tmp_path / "fw.bin"
        src.write_bytes(_synthetic_bin())
        guard = FileGuard(tmp_path / "work")
        record = guard.protect(src, job_id="test004")
        # Modificar a cópia de trabalho (precisa remover read-only primeiro)
        import stat
        p = Path(record.work_path)
        p.chmod(p.stat().st_mode | stat.S_IWRITE)
        p.write_bytes(b"\x00" * 1024)
        assert not record.verify()

    def test_protect_nonexistent_raises(self, tmp_path):
        guard = FileGuard(tmp_path / "work")
        with pytest.raises(FileNotFoundError):
            guard.protect(tmp_path / "nao_existe.bin", job_id="x")

    def test_sha256_deterministic(self, tmp_path):
        src = tmp_path / "fw.bin"
        data = _synthetic_bin(2048)
        src.write_bytes(data)
        h1 = _sha256(src)
        h2 = _sha256(src)
        assert h1 == h2 == hashlib.sha256(data).hexdigest()


# ── pipeline — detecção de formato e arquitetura ──────────────────────────────

class TestFormatDetection:
    def test_srec(self):
        assert _detect_format(_srecord_header()) == PFmt.MOTOROLA_SREC

    def test_intel_hex(self):
        assert _detect_format(_intel_hex_simple()) == PFmt.INTEL_HEX

    def test_elf(self):
        assert _detect_format(b"\x7fELF\x01\x01\x01\x00" + b"\x00" * 56) == PFmt.ELF

    def test_pe(self):
        assert _detect_format(b"MZ" + b"\x00" * 62) == PFmt.PE

    def test_binary_raw(self):
        assert _detect_format(_synthetic_bin()) == PFmt.BINARY_RAW

    def test_empty(self):
        assert _detect_format(b"") == PFmt.UNKNOWN


class TestArchDetection:
    def test_arm_thumb_bx_lr(self):
        # BX LR (Thumb) pattern
        data = b"\x00" * 256 + b"\x70\x47" + b"\x00" * 3838
        arch, conf = _detect_arch_heuristic(data, PFmt.BINARY_RAW)
        assert arch == IdentifiedArch.ARM

    def test_unknown_random(self):
        import os
        data = os.urandom(4096)
        arch, conf = _detect_arch_heuristic(data, PFmt.BINARY_RAW)
        # Pode ser qualquer coisa, mas não deve travar
        assert isinstance(arch, IdentifiedArch)

    def test_too_short(self):
        arch, conf = _detect_arch_heuristic(b"\x00\x01", PFmt.BINARY_RAW)
        assert arch == IdentifiedArch.UNKNOWN
        assert conf == "none"


# ── pipeline — run completo com dados sintéticos ──────────────────────────────

class TestREPipeline:
    def test_run_binary_raw(self, tmp_path):
        fw = tmp_path / "synth_ecu.bin"
        fw.write_bytes(_synthetic_bin(4096))
        pipeline = REPipeline(work_root=tmp_path / "work")
        report = pipeline.run(fw, run_ghidra=False)
        assert report.sha256 != ""
        assert report.size_bytes == 4096
        assert report.detected_format == PFmt.BINARY_RAW

    def test_run_nonexistent_file(self, tmp_path):
        pipeline = REPipeline(work_root=tmp_path / "work")
        report = pipeline.run(tmp_path / "nao_existe.bin", run_ghidra=False)
        assert not report.sha256  # sha256 vazio = falha

    def test_force_arch(self, tmp_path):
        fw = tmp_path / "fw.bin"
        fw.write_bytes(_synthetic_bin())
        pipeline = REPipeline(work_root=tmp_path / "work")
        report = pipeline.run(fw, force_arch=IdentifiedArch.TRICORE, run_ghidra=False)
        assert report.detected_arch == IdentifiedArch.TRICORE
        assert report.arch_confidence == "manual"

    def test_report_summary_contains_sha256(self, tmp_path):
        fw = tmp_path / "fw.bin"
        fw.write_bytes(_synthetic_bin())
        pipeline = REPipeline(work_root=tmp_path / "work")
        report = pipeline.run(fw, run_ghidra=False)
        summary = report.summary()
        assert report.sha256[:16] in summary

    def test_srec_format_detected(self, tmp_path):
        fw = tmp_path / "fw.s19"
        fw.write_bytes(_srecord_header())
        pipeline = REPipeline(work_root=tmp_path / "work")
        report = pipeline.run(fw, run_ghidra=False)
        assert report.detected_format == PFmt.MOTOROLA_SREC


# ── repro_native ──────────────────────────────────────────────────────────────

class TestReproNative:
    def test_diff_stub_counts_changes(self):
        d = DiffStub()
        ori = b"\x00" * 100
        mod = b"\x00" * 50 + b"\xFF" * 50
        result = d.diff(ori, mod)
        assert result.changed_bytes == 50
        assert result.total_bytes == 100

    def test_diff_identical(self):
        d = DiffStub()
        data = b"\xAB\xCD" * 50
        result = d.diff(data, data)
        assert result.changed_bytes == 0

    def test_dtc_detector_finds_dtcs(self):
        d = DtcDetectorStub()
        # Binário sintético com DTCs embutidos em ASCII
        data = b"\x00" * 100 + b"P0300 P0301 B0001" + b"\x00" * 100
        result = d.detect(data)
        assert "P0300" in result.dtcs
        assert "P0301" in result.dtcs

    def test_dtc_detector_no_false_positives_in_zeros(self):
        d = DtcDetectorStub()
        result = d.detect(b"\x00" * 1024)
        assert result.dtcs == []

    def test_connectors_status(self):
        rc = ReproNativeConnectors()
        s = rc.status()
        assert "api_url" in s
        assert "fingerprint" in s
        assert "diff" in s
        assert s["diff"] is True  # stub built-in está disponível

    def test_fingerprint_stub_not_matched(self):
        rc = ReproNativeConnectors()
        result = rc.fingerprint.fingerprint(b"\x00" * 256)
        assert not result.matched
