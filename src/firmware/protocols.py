"""
Especificações de protocolos de comunicação automotiva.
Dados de documentação pública. Fonte e data registradas.
Simulação e modelagem aqui; comunicação real com hardware exige aprovação por sessão.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProtocolLayer(str, Enum):
    PHYSICAL  = "physical"
    DATALINK  = "datalink"
    TRANSPORT = "transport"
    SESSION   = "session"
    APP       = "application"


@dataclass
class ServiceID:
    sid: int
    name: str
    description: str


@dataclass
class ProtocolSpec:
    name: str
    full_name: str
    standard: str
    description: str
    layer: ProtocolLayer
    typical_baud: list[int]
    services: list[ServiceID]
    notes: str
    source: str = "ISO standard / public documentation"

    def summary(self) -> str:
        return f"{self.name} ({self.standard}) — {self.description}"


_UDS_SERVICES = [
    ServiceID(0x10, "DiagnosticSessionControl", "Muda sessão diagnóstica (default/extended/programming)"),
    ServiceID(0x11, "ECUReset", "Reinicia a ECU (soft/hard/key off)"),
    ServiceID(0x14, "ClearDiagnosticInformation", "Apaga DTCs da memória"),
    ServiceID(0x19, "ReadDTCInformation", "Lê DTCs com status e dados de freeze frame"),
    ServiceID(0x22, "ReadDataByIdentifier", "Lê parâmetro por DID (ex: VIN, versão SW)"),
    ServiceID(0x23, "ReadMemoryByAddress", "Lê memória por endereço e tamanho"),
    ServiceID(0x27, "SecurityAccess", "Desafio/resposta para desbloqueio (seed&key)"),
    ServiceID(0x28, "CommunicationControl", "Habilita/desabilita comunicação de rede"),
    ServiceID(0x2E, "WriteDataByIdentifier", "Escreve parâmetro por DID"),
    ServiceID(0x31, "RoutineControl", "Executa rotina interna da ECU"),
    ServiceID(0x34, "RequestDownload", "Solicita download (gravação) de dados"),
    ServiceID(0x35, "RequestUpload", "Solicita upload (leitura) de dados"),
    ServiceID(0x36, "TransferData", "Transfere bloco de dados"),
    ServiceID(0x37, "RequestTransferExit", "Encerra transferência"),
    ServiceID(0x3E, "TesterPresent", "Keep-alive para manter sessão ativa"),
]

_KWP2000_SERVICES = [
    ServiceID(0x10, "StartDiagnosticSession", "Inicia sessão (similar ao UDS 0x10)"),
    ServiceID(0x11, "ECUReset", "Reset da ECU"),
    ServiceID(0x14, "ClearDiagnosticInformation", "Apaga DTCs"),
    ServiceID(0x18, "ReadDTCByStatus", "Lê DTCs por status"),
    ServiceID(0x1A, "ReadECUIdentification", "Lê identificação da ECU"),
    ServiceID(0x21, "ReadDataByLocalIdentifier", "Lê dado por local ID"),
    ServiceID(0x23, "ReadMemoryByAddress", "Lê memória por endereço"),
    ServiceID(0x27, "SecurityAccess", "Desafio/resposta (seed&key)"),
    ServiceID(0x34, "RequestDownload", "Solicita download"),
    ServiceID(0x36, "TransferData", "Transfere dados"),
    ServiceID(0x3E, "TesterPresent", "Keep-alive"),
]

PROTOCOLS: list[ProtocolSpec] = [
    ProtocolSpec(
        name="UDS",
        full_name="Unified Diagnostic Services",
        standard="ISO 14229",
        description="Protocolo diagnóstico moderno, universal, sobre CAN/LIN/IP",
        layer=ProtocolLayer.SESSION,
        typical_baud=[500000, 1000000],
        services=_UDS_SERVICES,
        notes="Padrão atual para ECUs 2008+. CAN frame: até 8 bytes. Com CAN-FD: até 64 bytes.",
    ),
    ProtocolSpec(
        name="ISO-TP",
        full_name="ISO Transport Protocol",
        standard="ISO 15765-2",
        description="Protocolo de transporte sobre CAN — permite mensagens > 8 bytes",
        layer=ProtocolLayer.TRANSPORT,
        typical_baud=[500000, 1000000],
        services=[],
        notes="Single Frame ≤ 7 bytes. First Frame + Consecutive Frame para mensagens maiores.",
    ),
    ProtocolSpec(
        name="KWP2000",
        full_name="Keyword Protocol 2000",
        standard="ISO 14230",
        description="Protocolo diagnóstico predecessor do UDS — K-Line ou CAN",
        layer=ProtocolLayer.SESSION,
        typical_baud=[10400],
        services=_KWP2000_SERVICES,
        notes="Muito usado em ECUs 1998–2008. K-Line: 10.4 kbps. Inicialização por 5 baud ou fast init.",
    ),
    ProtocolSpec(
        name="CAN",
        full_name="Controller Area Network",
        standard="ISO 11898",
        description="Barramento de comunicação multiponto para ECUs automotivas",
        layer=ProtocolLayer.DATALINK,
        typical_baud=[125000, 250000, 500000, 1000000],
        services=[],
        notes="2.0A (11-bit ID) e 2.0B (29-bit ID). Prioritário por arbitragem. CAN-FD até 8 Mbps.",
    ),
    ProtocolSpec(
        name="K-Line",
        full_name="ISO 9141-2 K-Line",
        standard="ISO 9141-2",
        description="Linha serial de diagnóstico — single wire, nível 12V",
        layer=ProtocolLayer.PHYSICAL,
        typical_baud=[10400],
        services=[],
        notes="Usado em veículos até ~2008. OBD-II pino 7. Init por 5 baud: 0x33 → KB1, KB2.",
    ),
    ProtocolSpec(
        name="OBD-II",
        full_name="On-Board Diagnostics II",
        standard="SAE J1979 / ISO 15031",
        description="Interface padronizada de diagnóstico — acesso a PIDs e DTCs",
        layer=ProtocolLayer.APP,
        typical_baud=[250000, 500000],
        services=[
            ServiceID(0x01, "ShowCurrentData", "Lê PID de dados em tempo real"),
            ServiceID(0x02, "ShowFreezeFrame", "Lê freeze frame do DTC"),
            ServiceID(0x03, "ShowStoredCodes", "Lista DTCs confirmados"),
            ServiceID(0x04, "ClearCodes", "Apaga DTCs e dados de prontidão"),
            ServiceID(0x07, "ShowPendingCodes", "Lista DTCs pendentes"),
            ServiceID(0x09, "RequestVehicleInfo", "VIN, versão de calibração, CVN"),
        ],
        notes="Obrigatório nos EUA desde 1996. Brasil desde 2007 (Proconve P-7).",
    ),
]


def get_protocol(name: str) -> Optional[ProtocolSpec]:
    return next((p for p in PROTOCOLS if p.name.upper() == name.upper()), None)


def list_protocols() -> list[ProtocolSpec]:
    return PROTOCOLS
