import uuid
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Message:
    role: str   # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)
    model: str = ""
    cost_usd: float = 0.0


@dataclass
class Session:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = field(default_factory=time.time)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add(self, role: str, content: str, model: str = "", cost_usd: float = 0.0) -> Message:
        msg = Message(role=role, content=content, model=model, cost_usd=cost_usd)
        self.messages.append(msg)
        return msg

    def to_api_messages(self) -> List[Dict]:
        return [
            {"role": m.role, "content": m.content}
            for m in self.messages
            if m.role in ("user", "assistant")
        ]

    def total_cost(self) -> float:
        return sum(m.cost_usd for m in self.messages)

    def last_n(self, n: int) -> List[Message]:
        return self.messages[-n:]
