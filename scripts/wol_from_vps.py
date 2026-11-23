#!/usr/bin/env python3
"""
Wake-on-LAN — envia magic packet do VPS para ligar o PC.

Uso:
  python wol_from_vps.py <MAC> [broadcast] [porta]

Exemplos:
  python wol_from_vps.py AA:BB:CC:DD:EE:FF
  python wol_from_vps.py AA:BB:CC:DD:EE:FF 192.168.1.255
  python wol_from_vps.py AA:BB:CC:DD:EE:FF 255.255.255.255 9

Pré-requisito no roteador:
  Encaminhar UDP porta 9 (ou 7) para 192.168.X.255 (broadcast da rede local)
  ou diretamente para o IP do PC alvo.

Como descobrir o MAC do PC (executar no PC Windows):
  getmac /v /fo list | findstr "Endere"
  ou
  ipconfig /all | findstr "Fisico"
"""
from __future__ import annotations

import re
import socket
import sys


def parse_mac(mac: str) -> bytes:
    clean = re.sub(r"[^0-9a-fA-F]", "", mac)
    if len(clean) != 12:
        raise SystemExit(f"MAC inválido: '{mac}'. Use AA:BB:CC:DD:EE:FF")
    return bytes.fromhex(clean)


def send_wol(mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> None:
    mac_bytes = parse_mac(mac)
    packet = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.connect((broadcast, port))
        s.send(packet)
    print(f"Magic packet enviado para {mac} via {broadcast}:{port}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    mac_arg       = sys.argv[1]
    bcast_arg     = sys.argv[2] if len(sys.argv) > 2 else "255.255.255.255"
    port_arg      = int(sys.argv[3]) if len(sys.argv) > 3 else 9
    send_wol(mac_arg, bcast_arg, port_arg)
