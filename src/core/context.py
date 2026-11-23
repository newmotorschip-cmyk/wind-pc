import time
import os
from dataclasses import dataclass, field
from typing import List

DAILY_BUDGET_USD = float(os.getenv("WIND_DAILY_BUDGET", "2.0"))


@dataclass
class UsageRecord:
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    task_type: str


class ContextManager:
    def __init__(self, daily_budget: float = DAILY_BUDGET_USD):
        self.daily_budget = daily_budget
        self._usage: List[UsageRecord] = []

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        task_type: str = "general",
    ) -> None:
        self._usage.append(
            UsageRecord(
                timestamp=time.time(),
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                task_type=task_type,
            )
        )

    @property
    def daily_cost(self) -> float:
        cutoff = time.time() - 86400
        return sum(u.cost_usd for u in self._usage if u.timestamp >= cutoff)

    @property
    def remaining(self) -> float:
        return max(0.0, self.daily_budget - self.daily_cost)

    def can_spend(self, estimate: float = 0.001) -> bool:
        return self.daily_cost + estimate <= self.daily_budget

    def summary(self) -> dict:
        cutoff = time.time() - 86400
        today = [u for u in self._usage if u.timestamp >= cutoff]
        return {
            "daily_cost_usd": round(self.daily_cost, 5),
            "daily_budget_usd": self.daily_budget,
            "remaining_usd": round(self.remaining, 5),
            "calls_today": len(today),
            "input_tokens_today": sum(u.input_tokens for u in today),
            "output_tokens_today": sum(u.output_tokens for u in today),
        }
