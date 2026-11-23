"""
Wake-on-LAN — envia magic packet para ligar um PC remotamente.

Requisitos no PC alvo:
  1. WoL habilitado no BIOS/UEFI (procure "Wake on LAN" ou "Power on by PCI-E/PCI")
  2. Adaptador de rede configurado para WoL (Gerenciador de Dispositivos →
     Propriedades do adaptador → Gerenciamento de energia → permitir acordar)

Para uso remoto (fora da rede local):
  - Configure o roteador para encaminhar UDP porta 9 para 192.168.X.255 (broadcast da rede)
  - Execute wol_from_vps.py no servidor VPS passando o MAC do PC
"""
from __future__ import annotations

import re
import socket


def _parse_mac(mac: str) -> bytes:
    """Converte string MAC para bytes. Aceita AA:BB:CC:DD:EE:FF ou AA-BB-CC-DD-EE-FF."""
    mac_clean = re.sub(r"[^0-9a-fA-F]", "", mac)
    if len(mac_clean) != 12:
        raise ValueError(
            f"MAC inválido: '{mac}'. Use formato AA:BB:CC:DD:EE:FF"
        )
    return bytes.fromhex(mac_clean)


def send_magic_packet(
    mac: str,
    broadcast: str = "255.255.255.255",
    port: int = 9,
) -> None:
    """
    Envia magic packet WoL para ligar o PC remotamente.

    mac:       endereço MAC do PC alvo (ex: "AA:BB:CC:DD:EE:FF")
    broadcast: endereço de broadcast — use "255.255.255.255" para redes simples
               ou "192.168.1.255" para a rede local específica
    port:      porta UDP padrão WoL (9 ou 7)
    """
    mac_bytes = _parse_mac(mac)
    # Magic packet: 6x 0xFF + 16 repetições do MAC
    packet = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.connect((broadcast, port))
        s.send(packet)


def magic_packet_bytes(mac: str) -> bytes:
    """Retorna os bytes do magic packet sem enviar (útil para testes)."""
    mac_bytes = _parse_mac(mac)
    return b"\xff" * 6 + mac_bytes * 16
