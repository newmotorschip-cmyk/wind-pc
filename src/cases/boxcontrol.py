"""
Contrato de integração com o BoxControl.
BoxControl é o sistema de gestão da REPROTECH (Python/React/Node.js/PostgreSQL).

Esta interface define como a WIND se comunica com o BoxControl.
A implementação real depende do BoxControl estar acessível na VPS ou localmente.
Enquanto isso, o stub retorna dados vazios sem quebrar o restante da WIND.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ServiceOrder:
    """Ordem de serviço do BoxControl (somente leitura pela WIND)."""
    id: str
    vehicle_placa: str
    vehicle_modelo: str
    queixa: str
    status: str
    technician: str
    created_at: float
    total_brl: float = 0.0
    dtcs: list[str] = None

    def __post_init__(self):
        if self.dtcs is None:
            self.dtcs = []


class BoxControlConnector(ABC):
    """Interface para integração com BoxControl."""

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[ServiceOrder]:
        """Busca uma OS pelo ID."""
        ...

    @abstractmethod
    def list_open_orders(self) -> list[ServiceOrder]:
        """Lista OS em aberto."""
        ...

    @abstractmethod
    def get_vehicle_history(self, placa: str) -> list[ServiceOrder]:
        """Histórico de OS de um veículo."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o BoxControl está acessível."""
        ...


class BoxControlStub(BoxControlConnector):
    """
    Stub para quando o BoxControl não está disponível.
    Usado enquanto a integração real não está implementada.
    """

    def get_order(self, order_id: str) -> Optional[ServiceOrder]:
        return None

    def list_open_orders(self) -> list[ServiceOrder]:
        return []

    def get_vehicle_history(self, placa: str) -> list[ServiceOrder]:
        return []

    def is_available(self) -> bool:
        return False


class BoxControlHTTPConnector(BoxControlConnector):
    """
    Conector HTTP real para o BoxControl.
    Requer BOXCONTROL_API_URL e BOXCONTROL_API_KEY no ambiente.
    Implementação completa na Fase 3+ quando o BoxControl estiver acessível.
    """

    def __init__(self, base_url: str = "", api_key: str = "") -> None:
        import os
        self._base_url = base_url or os.getenv("BOXCONTROL_API_URL", "")
        self._api_key  = api_key  or os.getenv("BOXCONTROL_API_KEY", "")

    def is_available(self) -> bool:
        if not self._base_url:
            return False
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self._base_url}/health",
                headers={"X-API-Key": self._api_key},
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def get_order(self, order_id: str) -> Optional[ServiceOrder]:
        # TODO: implementar quando BoxControl estiver acessível
        return None

    def list_open_orders(self) -> list[ServiceOrder]:
        return []

    def get_vehicle_history(self, placa: str) -> list[ServiceOrder]:
        return []


def get_connector() -> BoxControlConnector:
    """Retorna o conector disponível: real se configurado, stub caso contrário."""
    conn = BoxControlHTTPConnector()
    if conn.is_available():
        return conn
    return BoxControlStub()
