"""Local market provider and deterministic feature calculation."""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.schemas import MarketSnapshot

DATA_FILE = Path(__file__).parent.parent / "data" / "market_data.json"
REQUIRED_FIELDS = set(MarketSnapshot.model_fields)


class SymbolNotFoundError(ValueError):
    pass


class IncompleteMarketDataError(ValueError):
    pass


@dataclass(frozen=True)
class MarketFeatures:
    price_momentum_percent: float
    twenty_day_momentum_percent: float
    moving_average_position_percent: float
    volume_ratio: float
    volatility_percent: float
    drawdown_percent: float


class MarketDataProvider(Protocol):
    def list_snapshots(self) -> list[MarketSnapshot]: ...

    def get_snapshot(self, symbol: str) -> MarketSnapshot: ...


class SimulatedMarketDataProvider:
    def __init__(self, data_file: Path = DATA_FILE) -> None:
        self.data_file = data_file

    def _records(self) -> list[dict[str, object]]:
        records = json.loads(self.data_file.read_text())
        if not isinstance(records, list):
            raise IncompleteMarketDataError("Market fixture must contain a list")
        return records

    def list_snapshots(self) -> list[MarketSnapshot]:
        snapshots: list[MarketSnapshot] = []
        for record in self._records():
            missing = REQUIRED_FIELDS - record.keys()
            if missing:
                symbol = record.get("symbol", "unknown")
                raise IncompleteMarketDataError(f"{symbol} is missing: {', '.join(sorted(missing))}")
            snapshots.append(MarketSnapshot.model_validate(record))
        return snapshots

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        normalized = symbol.strip().upper()
        for snapshot in self.list_snapshots():
            if snapshot.symbol == normalized:
                return snapshot
        raise SymbolNotFoundError(f"Unknown stock symbol: {normalized}")


def calculate_features(snapshot: MarketSnapshot) -> MarketFeatures:
    if snapshot.previous_close <= 0 or snapshot.twenty_day_moving_average <= 0 or snapshot.average_volume <= 0:
        raise IncompleteMarketDataError("Price, moving average, and volume denominators must be positive")
    return MarketFeatures(
        price_momentum_percent=round((snapshot.current_price / snapshot.previous_close - 1) * 100, 2),
        twenty_day_momentum_percent=snapshot.twenty_day_return,
        moving_average_position_percent=round((snapshot.current_price / snapshot.twenty_day_moving_average - 1) * 100, 2),
        volume_ratio=round(snapshot.current_volume / snapshot.average_volume, 2),
        volatility_percent=snapshot.volatility,
        drawdown_percent=snapshot.drawdown,
    )
