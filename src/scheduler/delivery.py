"""ProactiveDelivery — entrega alertas proativos via NotificationManager."""
from __future__ import annotations

from .proactive import ProactiveMonitor


class ProactiveDelivery:
    """
    Ponte entre ProactiveMonitor e NotificationManager.
    Verifica alertas e os entrega via todos os canais disponíveis
    (console, arquivo, Telegram se configurado).
    """

    def __init__(self, monitor: ProactiveMonitor, manager) -> None:
        self._monitor = monitor
        self._manager = manager

    def run(self) -> int:
        """Verifica e entrega alertas. Retorna número de alertas enviados."""
        alerts = self._monitor.check_all()
        if not alerts:
            return 0
        text = self._monitor.format_alerts(alerts)
        self._manager.warning("WIND: Alertas Proativos", text)
        return len(alerts)

    def run_and_report(self) -> str:
        """Verifica, entrega (se houver) e retorna texto formatado dos alertas."""
        alerts = self._monitor.check_all()
        summary = self._monitor.format_alerts(alerts)
        if alerts:
            self._manager.warning("WIND: Alertas Proativos", summary)
        return summary

    def channels_active(self) -> list[str]:
        """Retorna nomes dos canais de notificação disponíveis."""
        return self._manager.available_channels()
