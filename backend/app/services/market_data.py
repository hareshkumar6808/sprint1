"""Local market provider and deterministic feature calculation."""
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from app.config import get_settings

from app.schemas import MarketSnapshot

DATA_FILE = Path(__file__).parent.parent / "data" / "market_data.json"
REQUIRED_FIELDS = {name for name, field in MarketSnapshot.model_fields.items() if field.is_required()}


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
            snapshots.append(MarketSnapshot.model_validate(record).model_copy(update={
                "provider_name": "local_simulated_fixture", "freshness": "fixture_timestamp"}))
        return snapshots

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        normalized = symbol.strip().upper()
        for snapshot in self.list_snapshots():
            if snapshot.symbol == normalized:
                return snapshot
        raise SymbolNotFoundError(f"Unknown stock symbol: {normalized}")


class AlphaVantageMarketDataProvider:
    """Optional live quote overlay; absent/invalid configuration never breaks the demo."""
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.fallback = SimulatedMarketDataProvider()

    def list_snapshots(self) -> list[MarketSnapshot]:
        return [self.get_snapshot(item.symbol) for item in self.fallback.list_snapshots()]

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        base = self.fallback.get_snapshot(symbol)
        response = httpx.get("https://www.alphavantage.co/query", timeout=5,
                             params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.api_key})
        response.raise_for_status()
        quote = response.json().get("Global Quote", {})
        price, previous, volume = float(quote["05. price"]), float(quote["08. previous close"]), int(quote["06. volume"])
        return base.model_copy(update={"current_price": price, "previous_close": previous,
            "current_volume": volume, "data_timestamp": datetime.now(timezone.utc), "simulated_data": False,
            "provider_name": "alpha_vantage", "freshness": "live_quote", "fallback_reason": None})


class ResilientMarketDataProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.simulated = SimulatedMarketDataProvider()
        self.live = AlphaVantageMarketDataProvider(settings.market_data_api_key) if settings.market_data_mode == "live" and settings.market_data_api_key else None

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        if self.live:
            try:
                return self.live.get_snapshot(symbol)
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                return self.simulated.get_snapshot(symbol).model_copy(update={
                    "fallback_reason": f"Live provider failed: {type(exc).__name__}"})
        reason = "Live mode not configured" if get_settings().market_data_mode == "live" else None
        return self.simulated.get_snapshot(symbol).model_copy(update={"fallback_reason": reason})

    def list_snapshots(self) -> list[MarketSnapshot]:
        return [self.get_snapshot(item.symbol) for item in self.simulated.list_snapshots()]


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
