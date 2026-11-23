"""
Interfaces de hardware para leitura/gravação de ECU.
Contrato ABC + stubs. Comunicação real NUNCA acontece sem:
  1. Aprovação por sessão do Felipe
  2. Backup verificado por hash (FileGuard)
  3. Checksum válido
  4. CalibrationProposal aprovada
Stubs retornam not_available. Integração real entra quando o hardware for configurado.
"""
from __future__ import annotations
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class InterfaceStatus(str, Enum):
    CONNECTED    = "connected"
    DISCONNECTED = "disconnected"
    ERROR        = "error"
    STUB         = "stub"


@dataclass
class ReadResult:
    success: bool
    data: bytes = b""
    address: int = 0
    length: int = 0
    duration_s: float = 0.0
    error: str = ""
    source: str = "stub"


@dataclass
class WriteResult:
    success: bool
    address: int = 0
    bytes_written: int = 0
    duration_s: float = 0.0
    error: str = ""
    source: str = "stub"


class FlashInterface(ABC):
    @abstractmethod
    def status(self) -> InterfaceStatus: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def read(self, address: int, length: int) -> ReadResult: ...

    @abstractmethod
    def write(self, address: int, data: bytes, proposal_id: str) -> WriteResult:
        """Requer proposal_id de proposta aprovada e aprovação explícita do Felipe na sessão."""
        ...

    @abstractmethod
    def interface_name(self) -> str: ...


class SM2Stub(FlashInterface):
    """
    Stub para Scanmatik SM2 Pro.
    Ativar configurando SM2_DEVICE_PORT no ambiente (ex: COM3).
    """

    def __init__(self) -> None:
        self._port = os.getenv("SM2_DEVICE_PORT", "")

    def interface_name(self) -> str:
        return "Scanmatik SM2"

    def status(self) -> InterfaceStatus:
        return InterfaceStatus.DISCONNECTED

    def is_available(self) -> bool:
        return False

    def read(self, address: int, length: int) -> ReadResult:
        return ReadResult(
            success=False,
            error="SM2 não disponível — configure SM2_DEVICE_PORT e instale driver.",
        )

    def write(self, address: int, data: bytes, proposal_id: str) -> WriteResult:
        return WriteResult(
            success=False,
            error="Gravação via SM2 não disponível. Configure SM2_DEVICE_PORT.",
        )


class BDMStub(FlashInterface):
    """Stub para interface BDM (Background Debug Mode)."""

    def interface_name(self) -> str:
        return "BDM Interface"

    def status(self) -> InterfaceStatus:
        return InterfaceStatus.STUB

    def is_available(self) -> bool:
        return False

    def read(self, address: int, length: int) -> ReadResult:
        return ReadResult(success=False, error="BDM não conectado.")

    def write(self, address: int, data: bytes, proposal_id: str) -> WriteResult:
        return WriteResult(success=False, error="BDM não conectado.")


class FlashInterfaces:
    """Factory centralizada para interfaces de hardware."""

    def __init__(self) -> None:
        self._sm2 = SM2Stub()
        self._bdm = BDMStub()

    @property
    def sm2(self) -> FlashInterface:
        return self._sm2

    @property
    def bdm(self) -> FlashInterface:
        return self._bdm

    def status(self) -> dict:
        return {
            "sm2": {
                "name": self._sm2.interface_name(),
                "available": self._sm2.is_available(),
                "status": self._sm2.status().value,
            },
            "bdm": {
                "name": self._bdm.interface_name(),
                "available": self._bdm.is_available(),
                "status": self._bdm.status().value,
            },
        }
