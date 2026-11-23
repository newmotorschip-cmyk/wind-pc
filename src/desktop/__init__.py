"""Desktop Agent — executa ações no PC Windows a pedido da WIND."""
from .agent import DesktopAgent
from .wol import send_magic_packet

__all__ = ["DesktopAgent", "send_magic_packet"]
