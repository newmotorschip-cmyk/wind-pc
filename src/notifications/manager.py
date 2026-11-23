"""
Gerenciador de notificações da WIND.
Rota para múltiplos canais com fallback automático para ConsoleChannel.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .channel import (
    ConsoleChannel,
    FileChannel,
    Notification,
    NotifLevel,
    NotificationChannel,
    TelegramStub,
)


class NotificationManager:
    """
    Envia notificações para todos os canais disponíveis.
    ConsoleChannel é o fallback garantido.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        notif_path = (db_path.parent / "notifications.jsonl") if db_path else Path("data/notifications.jsonl")
        self._channels: list[NotificationChannel] = [
            ConsoleChannel(),
            FileChannel(notif_path),
            TelegramStub(),
        ]

    def add_channel(self, channel: NotificationChannel) -> None:
        self._channels.append(channel)

    def available_channels(self) -> list[str]:
        return [c.name() for c in self._channels if c.is_available()]

    def notify(
        self,
        title: str,
        body: str,
        level: NotifLevel = NotifLevel.INFO,
        source: str = "wind",
    ) -> dict[str, bool]:
        notif = Notification(title=title, body=body, level=level, source=source)
        results: dict[str, bool] = {}
        for channel in self._channels:
            if channel.is_available():
                results[channel.name()] = channel.send(notif)
        return results

    def alert(self, title: str, body: str) -> dict[str, bool]:
        return self.notify(title, body, NotifLevel.ALERT)

    def warning(self, title: str, body: str) -> dict[str, bool]:
        return self.notify(title, body, NotifLevel.WARNING)

    def info(self, title: str, body: str) -> dict[str, bool]:
        return self.notify(title, body, NotifLevel.INFO)

    def read_recent(self, limit: int = 20) -> list[Notification]:
        for channel in self._channels:
            if isinstance(channel, FileChannel):
                return channel.read_recent(limit)
        return []
