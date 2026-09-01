"""Deterministic analysis metrics."""
import json
from pathlib import Path
from typing import Any

from app.schemas import AgentOutput, AgentStatus, Profile

HISTORY_FILE = Path(__file__).parent.parent / "data" / "historical_signals.json"


def historical_accuracy(symbol: str, history_file: Path = HISTORY_FILE) -> float:
    rows = [row for row in json.loads(history_file.read_text()) if row.get("symbol") == symbol and "correct" in row]
    return round(sum(bool(row["correct"]) for row in rows) / len(rows) * 100, 2) if rows else 0.0


def _holding_weight(holding: dict[str, Any]) -> float:
    for key in ("weight", "allocation_percent", "percentage"):
        if key in holding:
            return float(holding[key])
    if "value" in holding:
        return float(holding["value"])
    if "quantity" in holding and "price" in holding:
        return float(holding["quantity"]) * float(holding["price"])
    return 0.0


def portfolio_concentration(profile: Profile) -> float:
    values = [_holding_weight(item) for item in profile.portfolio]
    values = [value for value in values if value > 0]
    if not values:
        return 0.0
    total = sum(values)
    weights = [value / total for value in values]
    largest = max(weights) * 100
    hhi = sum(weight * weight for weight in weights) * 100
    return round((largest + hhi) / 2, 2)


def data_completeness(agents: list[AgentOutput]) -> float:
    if not agents:
        return 0.0
    status_weights = {AgentStatus.completed: 1.0, AgentStatus.degraded: 0.6,
                      AgentStatus.unavailable: 0.0, AgentStatus.failed: 0.0}
    return round(sum(status_weights[agent.status] for agent in agents) / len(agents) * 100, 2)
