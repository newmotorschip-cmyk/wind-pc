"""
Canais de notificação da WIND.
ConsoleChannel: sempre disponível.
FileChannel: grava em data/notifications.jsonl.
TelegramStub: requer TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID.
"""
from __future__ import annotations

import json
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError


class NotifLevel(str, Enum):
    INFO    = "info"
    WARNING = "warning"
    ALERT   = "alert"


@dataclass
class Notification:
    title: str
    body: str
    level: NotifLevel = NotifLevel.INFO
    created_at: float = field(default_factory=time.time)
    source: str = "wind"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "body": self.body,
            "level": self.level.value,
            "created_at": self.created_at,
            "source": self.source,
        }

    def format_text(self) -> str:
        icon = {"info": "ℹ️", "warning": "⚠️", "alert": "🚨"}.get(self.level.value, "·")
        return f"{icon} [{self.title}]\n{self.body}"


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, notif: Notification) -> bool: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def name(self) -> str: ...


class ConsoleChannel(NotificationChannel):
    """Imprime notificações no terminal. Sempre disponível."""

    def name(self) -> str:
        return "console"

    def is_available(self) -> bool:
        return True

    def send(self, notif: Notification) -> bool:
        print(f"\n{notif.format_text()}\n", file=sys.stdout)
        return True


class FileChannel(NotificationChannel):
    """Grava notificações em JSONL (append-only). Sempre disponível."""

    def __init__(self, path: Path | str = "data/notifications.jsonl") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def name(self) -> str:
        return "file"

    def is_available(self) -> bool:
        return True

    def send(self, notif: Notification) -> bool:
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(notif.to_dict(), ensure_ascii=False) + "\n")
            return True
        except OSError:
            return False

    def read_recent(self, limit: int = 20) -> list[Notification]:
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        result = []
        for line in reversed(lines[-limit:]):
            try:
                d = json.loads(line)
                result.append(Notification(
                    title=d["title"], body=d["body"],
                    level=NotifLevel(d["level"]),
                    created_at=d.get("created_at", 0.0),
                    source=d.get("source", "wind"),
                ))
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        return result


class TelegramStub(NotificationChannel):
    """
    Envia notificações via Telegram Bot API.
    Requer: TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no ambiente.
    """

    def __init__(self) -> None:
        self._token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    def name(self) -> str:
        return "telegram"

    def is_available(self) -> bool:
        return bool(self._token and self._chat_id)

    def send(self, notif: Notification) -> bool:
        if not self.is_available():
            return False
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        text = notif.format_text()
        data = urlencode({"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"})
        req = Request(url, data=data.encode("utf-8"), method="POST")
        try:
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except (URLError, OSError):
            return False
