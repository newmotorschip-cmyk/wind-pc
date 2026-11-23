"""
Currículo de estudo da WIND — Fase 8.
Tópicos mantidos por Felipe e pela WIND. Sessões agendadas dentro do orçamento.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class StudyPriority(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class StudyStatus(str, Enum):
    PENDING    = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED  = "completed"
    DEFERRED   = "deferred"


@dataclass
class StudyItem:
    id: str
    topic: str
    description: str
    priority: StudyPriority = StudyPriority.MEDIUM
    status: StudyStatus = StudyStatus.PENDING
    tags: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)   # ids de pré-requisitos
    added_by: str = "Felipe"
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    notes: str = ""

    def summary_line(self) -> str:
        icon = {"pending": "📚", "in_progress": "▶️", "completed": "✅", "deferred": "⏸️"}.get(self.status.value, "·")
        return f"{icon} [{self.priority.value.upper()}] {self.topic[:60]}"

    def to_dict(self) -> dict:
        return {
            "id": self.id, "topic": self.topic, "description": self.description,
            "priority": self.priority.value, "status": self.status.value,
            "tags": self.tags, "prerequisites": self.prerequisites,
            "added_by": self.added_by, "created_at": self.created_at,
            "completed_at": self.completed_at, "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: dict) -> "StudyItem":
        return StudyItem(
            id=d["id"], topic=d["topic"], description=d["description"],
            priority=StudyPriority(d.get("priority", "medium")),
            status=StudyStatus(d.get("status", "pending")),
            tags=d.get("tags", []), prerequisites=d.get("prerequisites", []),
            added_by=d.get("added_by", "Felipe"),
            created_at=float(d.get("created_at", 0)),
            completed_at=float(d.get("completed_at", 0)),
            notes=d.get("notes", ""),
        )


# Currículo padrão da WIND — tópicos conhecidos ao criar
_DEFAULT_CURRICULUM: list[dict] = [
    {"id": "ecu-bosch-me9",    "topic": "Arquitetura Bosch ME9",
     "description": "Mapa de memória, serviços UDS, checksum CRC32-Bosch, peculiaridades do TriCore",
     "priority": "high", "tags": ["ecu", "bosch", "tricore"]},
    {"id": "ecu-bosch-med17",  "topic": "Arquitetura Bosch MED17",
     "description": "Diferenças ME9→MED17, compatibilidade A2L, proteções TProt",
     "priority": "high", "tags": ["ecu", "bosch", "med17"]},
    {"id": "ecu-edc17",        "topic": "Bosch EDC17 (diesel)",
     "description": "Variantes EDC17C, EDC17CP, EDC17CV. Proteções SCR/EGR legais",
     "priority": "high", "tags": ["ecu", "bosch", "diesel", "edc17"]},
    {"id": "ghidra-tricore",   "topic": "Ghidra: análise TriCore",
     "description": "Configuração de processador, loader, base address, funções de checksum",
     "priority": "high", "tags": ["ghidra", "tricore"]},
    {"id": "ghidra-superh",    "topic": "Ghidra: análise SuperH",
     "description": "SH7xxx, loader Renesas, estrutura típica de ECU Denso",
     "priority": "medium", "tags": ["ghidra", "superh", "denso"]},
    {"id": "protocol-uds",     "topic": "Protocolo UDS ISO 14229",
     "description": "Serviços de leitura, escrita e flashing. Seed/key. Timing parameters",
     "priority": "medium", "tags": ["protocolo", "uds"]},
    {"id": "protocol-isotp",   "topic": "Protocolo ISO-TP (ISO 15765-2)",
     "description": "Fragmentação CAN, flow control, padding, implementação Python",
     "priority": "medium", "tags": ["protocolo", "can", "isotp"]},
    {"id": "damos-a2l",        "topic": "Formato DAMOS/A2L",
     "description": "Estrutura de arquivo A2L, leitura com pyA2L ou parser próprio",
     "priority": "medium", "tags": ["damos", "a2l", "calibracao"]},
    {"id": "guardian-decisao", "topic": "Motor de decisão Guardian",
     "description": "Níveis A0-A4, envelopes, registro de decisão, auditoria",
     "priority": "low", "tags": ["guardian", "autonomia"]},
    {"id": "llm-contexto",     "topic": "Otimização de contexto para LLMs",
     "description": "Cache, contexto enxuto, skills sob demanda, medição de custo/qualidade",
     "priority": "low", "tags": ["llm", "otimizacao"]},
]


class Curriculum:
    def __init__(self, path: Path | str = "data/curriculum.json") -> None:
        self._path = Path(path)
        self._items: dict[str, StudyItem] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._items = {d["id"]: StudyItem.from_dict(d) for d in data}
                return
            except (json.JSONDecodeError, KeyError):
                pass
        # Inicializar com currículo padrão
        for d in _DEFAULT_CURRICULUM:
            d.setdefault("status", "pending")
            d.setdefault("tags", [])
            d.setdefault("prerequisites", [])
            d.setdefault("added_by", "WIND")
            d.setdefault("created_at", time.time())
            d.setdefault("completed_at", 0.0)
            d.setdefault("notes", "")
            item = StudyItem.from_dict(d)
            self._items[item.id] = item
        self._save()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([i.to_dict() for i in self._items.values()],
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, topic: str, description: str,
            priority: StudyPriority = StudyPriority.MEDIUM,
            tags: Optional[list[str]] = None,
            added_by: str = "Felipe") -> StudyItem:
        import uuid
        item = StudyItem(
            id=str(uuid.uuid4())[:8], topic=topic, description=description,
            priority=priority, tags=tags or [], added_by=added_by,
        )
        self._items[item.id] = item
        self._save()
        return item

    def get(self, item_id: str) -> Optional[StudyItem]:
        return self._items.get(item_id)

    def list_pending(self) -> list[StudyItem]:
        items = [i for i in self._items.values() if i.status == StudyStatus.PENDING]
        order = {StudyPriority.HIGH: 0, StudyPriority.MEDIUM: 1, StudyPriority.LOW: 2}
        return sorted(items, key=lambda i: order[i.priority])

    def list_all(self) -> list[StudyItem]:
        return list(self._items.values())

    def mark_in_progress(self, item_id: str) -> Optional[StudyItem]:
        item = self._items.get(item_id)
        if item:
            item.status = StudyStatus.IN_PROGRESS
            self._save()
        return item

    def mark_completed(self, item_id: str, notes: str = "") -> Optional[StudyItem]:
        item = self._items.get(item_id)
        if item:
            item.status       = StudyStatus.COMPLETED
            item.completed_at = time.time()
            item.notes        = notes
            self._save()
        return item

    def summary(self) -> str:
        total  = len(self._items)
        done   = sum(1 for i in self._items.values() if i.status == StudyStatus.COMPLETED)
        active = sum(1 for i in self._items.values() if i.status == StudyStatus.IN_PROGRESS)
        lines  = [f"Currículo WIND: {done}/{total} concluídos | {active} em andamento"]
        pending = self.list_pending()
        if pending:
            lines.append("Próximos tópicos:")
            for item in pending[:5]:
                lines.append(f"  {item.summary_line()}")
        return "\n".join(lines)
