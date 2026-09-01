"""Official Upstox quote and historical-candle adapters with bounded caching."""
from datetime import date, datetime, timedelta, timezone
from time import monotonic
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx

from app.config import get_settings
from app.schemas import Candle, Instrument, MarketQuote


class UpstoxError(RuntimeError): pass
class UpstoxAuthenticationError(UpstoxError): pass
class UpstoxRateLimitError(UpstoxError): pass
class UpstoxUnavailableError(UpstoxError): pass
class UpstoxResponseError(UpstoxError): pass


class UpstoxProvider:
    QUOTE_URL = "https://api.upstox.com/v2/market-quote/quotes"
    HISTORY_URL = "https://api.upstox.com/v3/historical-candle/{instrument_key}/days/1/{to_date}/{from_date}"

    def __init__(self, token: str, client: httpx.Client | None = None) -> None:
        self.token = token; self.settings = get_settings(); self.client = client or httpx.Client(
            timeout=self.settings.market_request_timeout_seconds)
        self._quote_cache: dict[str, tuple[float, MarketQuote]] = {}
        self._candle_cache: dict[str, tuple[float, list[Candle]]] = {}

    def _get(self, url: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self.client.get(url, headers={"Accept": "application/json",
                "Authorization": f"Bearer {self.token}"}, **kwargs)
        except httpx.TimeoutException as exc:
            raise UpstoxUnavailableError("Upstox request timed out") from exc
        except httpx.HTTPError as exc:
            raise UpstoxUnavailableError("Upstox provider unavailable") from exc
        if response.status_code in {401, 403}:
            raise UpstoxAuthenticationError("Upstox access token is invalid or expired")
        if response.status_code == 429:
            raise UpstoxRateLimitError("Upstox rate limit reached")
        if response.status_code >= 400:
            raise UpstoxUnavailableError(f"Upstox returned HTTP {response.status_code}")
        payload = response.json()
        if payload.get("status") != "success" or not isinstance(payload.get("data"), dict):
            raise UpstoxResponseError("Malformed Upstox response")
        return payload

    @staticmethod
    def _timestamp(value: object) -> datetime | None:
        if value in (None, ""):
            return None
        try:
            numeric = int(str(value)); return datetime.fromtimestamp(numeric / 1000, timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _market_status(provider_time: datetime | None) -> str:
        when = (provider_time or datetime.now(timezone.utc)).astimezone(ZoneInfo("Asia/Kolkata"))
        minutes = when.hour * 60 + when.minute
        return "closed" if when.weekday() >= 5 or minutes < 9 * 60 + 15 or minutes > 15 * 60 + 30 else "unknown"

    def quotes(self, instruments: list[Instrument]) -> list[MarketQuote]:
        now = monotonic(); results: list[MarketQuote] = []; missing: list[Instrument] = []
        for item in instruments:
            cached = self._quote_cache.get(item.instrument_key)
            if cached and now - cached[0] < self.settings.quote_cache_seconds:
                results.append(cached[1].model_copy(update={"data_mode": "cached", "freshness": "short-lived cache"}))
            else:
                missing.append(item)
        if not missing:
            return results
        payload = self._get(self.QUOTE_URL, params={"instrument_key": ",".join(item.instrument_key for item in missing)})
        for item in missing:
            raw = next((value for value in payload["data"].values()
                        if value.get("instrument_token") == item.instrument_key), None)
            if not raw or raw.get("last_price") is None:
                continue
            ohlc = raw.get("ohlc") or {}; previous = ohlc.get("close"); last = float(raw["last_price"])
            absolute = float(raw["net_change"]) if raw.get("net_change") is not None else (last - float(previous) if previous is not None else None)
            retrieved = datetime.now(timezone.utc); provider_time = self._timestamp(raw.get("timestamp") or raw.get("last_trade_time"))
            quote = MarketQuote(instrument_key=item.instrument_key, exchange=item.exchange, symbol=item.symbol,
                company_name=item.name, last_price=last, previous_close=previous, absolute_change=absolute,
                percentage_change=(absolute / float(previous) * 100 if absolute is not None and previous else None),
                open=ohlc.get("open"), high=ohlc.get("high"), low=ohlc.get("low"), close=ohlc.get("close"),
                volume=raw.get("volume"), provider_timestamp=provider_time, retrieved_at=retrieved,
                provider_name="upstox", data_mode="live", age_seconds=max(0, int((retrieved-provider_time).total_seconds())) if provider_time else None,
                freshness="exchange snapshot", market_status=self._market_status(provider_time))
            self._quote_cache[item.instrument_key] = (now, quote); results.append(quote)
        return results

    def candles(self, instrument_key: str, days: int = 120) -> list[Candle]:
        cached = self._candle_cache.get(instrument_key); now = monotonic()
        if cached and now - cached[0] < self.settings.candle_cache_seconds:
            return cached[1]
        end = date.today(); start = end - timedelta(days=days * 2)
        url = self.HISTORY_URL.format(instrument_key=quote(instrument_key, safe=""), to_date=end.isoformat(), from_date=start.isoformat())
        payload = self._get(url); raw_candles = payload["data"].get("candles")
        if not isinstance(raw_candles, list):
            raise UpstoxResponseError("Historical response has no candle list")
        unique: dict[datetime, Candle] = {}
        for row in raw_candles:
            try:
                candle = Candle(timestamp=row[0], open=row[1], high=row[2], low=row[3], close=row[4], volume=row[5])
                if candle.low <= min(candle.open, candle.close) <= candle.high and candle.low <= max(candle.open, candle.close) <= candle.high:
                    unique[candle.timestamp] = candle
            except (IndexError, TypeError, ValueError):
                continue
        normalized = sorted(unique.values(), key=lambda item: item.timestamp)[-days:]
        self._candle_cache[instrument_key] = (now, normalized)
        return normalized
