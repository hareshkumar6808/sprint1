"""Local market provider and deterministic feature calculation."""
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from app.config import get_settings

from app.schemas import MarketSnapshot
from app.schemas import Candle, Instrument
from app.services.upstox import UpstoxError, UpstoxProvider

DATA_FILE = Path(__file__).parent.parent / "data" / "market_data.json"
REQUIRED_FIELDS = {name for name, field in MarketSnapshot.model_fields.items() if field.is_required()}


class SymbolNotFoundError(ValueError):
    pass


class IncompleteMarketDataError(ValueError):
    pass


@dataclass(frozen=True)
class MarketFeatures:
    price_momentum_percent: float
    twenty_day_momentum_percent: float | None
    moving_average_position_percent: float | None
    volume_ratio: float | None
    volatility_percent: float
    drawdown_percent: float
    rsi: float | None = None


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
        self.upstox = UpstoxProvider(settings.upstox_access_token) if settings.market_data_mode == "live" and settings.market_data_provider == "upstox" and settings.upstox_access_token else None

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

    def get_instrument_snapshot(self, instrument: Instrument) -> MarketSnapshot:
        if not self.upstox:
            try:
                return self.get_snapshot(instrument.symbol).model_copy(update={"instrument_key": instrument.instrument_key,
                    "exchange": instrument.exchange, "fallback_reason": "Upstox live mode is not configured"})
            except SymbolNotFoundError as exc:
                raise IncompleteMarketDataError("Live Upstox data unavailable and no matching offline fixture exists") from exc
        try:
            quotes = self.upstox.quotes([instrument]); candles = self.upstox.candles(instrument.instrument_key)
            if not quotes:
                raise IncompleteMarketDataError("Upstox returned no quote for the selected instrument")
            return snapshot_from_market_data(instrument, quotes[0], candles)
        except UpstoxError as exc:
            try:
                return self.get_snapshot(instrument.symbol).model_copy(update={"instrument_key": instrument.instrument_key,
                    "exchange": instrument.exchange, "fallback_reason": str(exc)})
            except SymbolNotFoundError as missing:
                raise IncompleteMarketDataError(str(exc)) from missing


def calculate_features(snapshot: MarketSnapshot) -> MarketFeatures:
    if snapshot.previous_close <= 0:
        raise IncompleteMarketDataError("Previous close must be positive")
    return MarketFeatures(
        price_momentum_percent=round((snapshot.current_price / snapshot.previous_close - 1) * 100, 2),
        twenty_day_momentum_percent=snapshot.twenty_day_return,
        moving_average_position_percent=(round((snapshot.current_price / snapshot.twenty_day_moving_average - 1) * 100, 2)
                                         if snapshot.twenty_day_moving_average and snapshot.twenty_day_moving_average > 0 else None),
        volume_ratio=(round(snapshot.current_volume / snapshot.average_volume, 2)
                      if snapshot.average_volume and snapshot.average_volume > 0 else None),
        volatility_percent=snapshot.volatility,
        drawdown_percent=snapshot.drawdown,
        rsi=snapshot.rsi,
    )


def _return(closes: list[float], periods: int) -> float | None:
    return round((closes[-1] / closes[-periods - 1] - 1) * 100, 2) if len(closes) > periods and closes[-periods - 1] else None


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    changes = [closes[i] - closes[i - 1] for i in range(len(closes) - period, len(closes))]
    gain = sum(max(0, value) for value in changes) / period; loss = sum(max(0, -value) for value in changes) / period
    if loss == 0:
        return 100.0
    return round(100 - 100 / (1 + gain / loss), 2)


def snapshot_from_market_data(instrument: Instrument, quote: object, candles: list[Candle]) -> MarketSnapshot:
    from app.schemas import MarketQuote
    normalized_quote = MarketQuote.model_validate(quote)
    if len(candles) < 2:
        raise IncompleteMarketDataError("At least two valid candles are required")
    closes = [item.close for item in candles]; volumes = [item.volume for item in candles]
    warnings: list[str] = []
    five, twenty = _return(closes, 5), _return(closes, 20)
    if five is None: warnings.append("5-day return unavailable: insufficient history")
    if twenty is None: warnings.append("20-day return unavailable: insufficient history")
    average_volume = round(sum(volumes[-20:]) / 20) if len(volumes) >= 20 else None
    returns = [(closes[index] / closes[index-1] - 1) * 100 for index in range(1, len(closes))]
    mean = sum(returns[-20:]) / min(20, len(returns)); variance = sum((item-mean)**2 for item in returns[-20:]) / min(20, len(returns))
    moving_average = sum(closes[-20:]) / 20 if len(closes) >= 20 else None; peak = max(closes)
    return MarketSnapshot(symbol=instrument.symbol, company_name=instrument.name,
        current_price=normalized_quote.last_price, previous_close=normalized_quote.previous_close or closes[-2],
        five_day_return=five, twenty_day_return=twenty, twenty_day_moving_average=moving_average,
        current_volume=normalized_quote.volume if normalized_quote.volume is not None else volumes[-1],
        average_volume=average_volume, volatility=round(variance ** .5 * (252 ** .5), 2),
        drawdown=round((closes[-1] / peak - 1) * 100, 2), pe_ratio=None, revenue_growth=None,
        debt_to_equity_ratio=None, data_timestamp=normalized_quote.provider_timestamp or normalized_quote.retrieved_at,
        simulated_data=False, provider_name="upstox", freshness=normalized_quote.freshness,
        instrument_key=instrument.instrument_key, exchange=instrument.exchange, data_mode=normalized_quote.data_mode,
        retrieved_at=normalized_quote.retrieved_at, age_seconds=normalized_quote.age_seconds,
        market_status=normalized_quote.market_status, one_day_return=_return(closes, 1), rsi=_rsi(closes),
        indicator_warnings=warnings)
