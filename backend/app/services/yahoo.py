"""Free, no-key Yahoo Finance adapter for selected Indian instruments.

Yahoo is an unofficial market-data source. Values can be delayed and must never
be represented as exchange-certified or suitable for order execution.
"""
from __future__ import annotations

import math
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote as urlquote

import httpx

from app.config import get_settings
from app.schemas import Candle, Instrument, MarketQuote

DISCLAIMER = "Yahoo Finance free market data; delay is not guaranteed; not suitable for order execution."
SOURCE_CLASS = "Unofficial market-data provider"


class YahooError(RuntimeError): pass
class YahooMappingError(YahooError): pass
class YahooUnavailableError(YahooError): pass
class YahooResponseError(YahooError): pass


def yahoo_symbol(instrument: Instrument) -> str:
    symbol = instrument.symbol.strip().upper()
    if not symbol or any(char.isspace() for char in symbol):
        raise YahooMappingError("Instrument has no valid Yahoo symbol mapping")
    suffix = {"NSE": ".NS", "BSE": ".BO"}.get(instrument.exchange)
    if not suffix:
        raise YahooMappingError("Yahoo supports only mapped NSE/BSE instruments")
    return f"{symbol}{suffix}"


def _number(value: object, *, required: bool = False) -> float | None:
    if value is None:
        if required: raise YahooResponseError("Yahoo response omitted a required price")
        return None
    try: result = float(value)
    except (TypeError, ValueError) as exc: raise YahooResponseError("Yahoo returned an invalid numeric field") from exc
    if not math.isfinite(result): raise YahooResponseError("Yahoo returned a non-finite numeric field")
    return result


class YahooFinanceProvider:
    CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    def __init__(self, client: httpx.Client | None = None, *, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        settings = get_settings(); self.settings = settings; self.clock = clock; self.sleep = sleep
        self.client = client or httpx.Client(timeout=settings.yahoo_request_timeout_seconds,
                                             headers={"User-Agent": "FinSync-Intelligence/1.0"})
        self._quote_cache: dict[str, tuple[float, MarketQuote]] = {}
        self._candle_cache: dict[str, tuple[float, list[Candle]]] = {}
        self._lock = threading.Lock(); self._inflight: dict[str, threading.Event] = {}
        self._failures = 0; self._cooldown_until = 0.0

    def _request(self, instrument: Instrument, *, interval: str, range_: str) -> dict[str, Any]:
        mapped = yahoo_symbol(instrument); key = f"{mapped}:{interval}:{range_}"
        now = self.clock()
        if now < self._cooldown_until:
            raise YahooUnavailableError("Yahoo Finance is temporarily paused after repeated failures; retry later")
        with self._lock:
            event = self._inflight.get(key)
            if event is None: event = self._inflight[key] = threading.Event(); owner = True
            else: owner = False
        if not owner:
            event.wait(self.settings.yahoo_request_timeout_seconds)
            cache = self._quote_cache if interval == "1m" else self._candle_cache
            cached = cache.get(mapped)
            if cached: return {"_coalesced": cached[1]}
            raise YahooUnavailableError("Concurrent Yahoo Finance request did not complete")
        try:
            last_error: Exception | None = None
            for attempt in range(3):
                try:
                    response = self.client.get(self.CHART_URL.format(symbol=urlquote(mapped, safe="")),
                                               params={"interval": interval, "range": range_, "events": "div,splits"})
                    if response.status_code == 429: raise YahooUnavailableError("Yahoo Finance rate limit reached")
                    response.raise_for_status(); payload = response.json()
                    chart = payload.get("chart") if isinstance(payload, dict) else None
                    results = chart.get("result") if isinstance(chart, dict) else None
                    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
                        description = "Yahoo Finance has no data for this listing" if isinstance(chart, dict) and chart.get("error") else "Yahoo Finance returned an unexpected response"
                        raise YahooResponseError(description)
                    self._failures = 0; return results[0]
                except (httpx.HTTPError, ValueError, YahooError) as exc:
                    last_error = exc
                    if attempt < 2: self.sleep(0.1 * (2 ** attempt))
            self._failures += 1
            if self._failures >= 3: self._cooldown_until = self.clock() + 30
            if isinstance(last_error, YahooError): raise last_error
            raise YahooUnavailableError("Yahoo Finance request failed; retry or choose another provider") from last_error
        finally:
            with self._lock: self._inflight.pop(key, None); event.set()

    @staticmethod
    def _validate_identity(result: dict[str, Any], expected: str) -> dict[str, Any]:
        meta = result.get("meta")
        if not isinstance(meta, dict) or str(meta.get("symbol", "")).upper() != expected.upper():
            raise YahooMappingError("Yahoo listing identity did not match the selected instrument")
        return meta

    def quote(self, instrument: Instrument) -> MarketQuote:
        mapped = yahoo_symbol(instrument); now = self.clock(); cached = self._quote_cache.get(mapped)
        if cached and now - cached[0] < self.settings.yahoo_quote_cache_seconds:
            return cached[1].model_copy(update={"data_mode": "cached", "cache_status": "hit",
                                                "freshness": "recent Yahoo cache"})
        result = self._request(instrument, interval="1m", range_="5d")
        if "_coalesced" in result: return result["_coalesced"].model_copy(update={"cache_status": "coalesced"})
        meta = self._validate_identity(result, mapped)
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators") or {}; quote_sets = indicators.get("quote") or []
        rows = quote_sets[0] if quote_sets and isinstance(quote_sets[0], dict) else {}
        closes = rows.get("close") or []
        valid = [(index, value) for index, value in enumerate(closes) if value is not None]
        price = _number(meta.get("regularMarketPrice") if meta.get("regularMarketPrice") is not None else (valid[-1][1] if valid else None), required=True)
        index = valid[-1][0] if valid else max(0, len(timestamps)-1)
        previous = _number(meta.get("chartPreviousClose") or meta.get("previousClose"))
        retrieved = datetime.now(timezone.utc)
        stamp_value = meta.get("regularMarketTime") or (timestamps[index] if index < len(timestamps) else None)
        try: provider_time = datetime.fromtimestamp(int(stamp_value), timezone.utc) if stamp_value else None
        except (TypeError, ValueError, OSError) as exc: raise YahooResponseError("Yahoo returned an invalid quote timestamp") from exc
        volume_value = (rows.get("volume") or [None] * (index + 1))[index] if index < len(rows.get("volume") or []) else None
        volume = int(volume_value) if volume_value is not None else None
        if volume is not None and volume < 0: raise YahooResponseError("Yahoo returned negative volume")
        field = lambda name: _number((rows.get(name) or [None] * (index + 1))[index] if index < len(rows.get(name) or []) else None)
        absolute = price - previous if previous is not None else None
        state = str(meta.get("marketState") or "").lower()
        market_status = "open" if state in {"regular", "pre", "post"} else ("closed" if state in {"closed", "postpost"} else "unknown")
        age = max(0, int((retrieved-provider_time).total_seconds())) if provider_time else None
        quote = MarketQuote(instrument_key=instrument.instrument_key, exchange=instrument.exchange,
            symbol=instrument.symbol, company_name=instrument.name, provider_symbol=mapped, last_price=price,
            previous_close=previous, absolute_change=absolute,
            percentage_change=(absolute / previous * 100 if absolute is not None and previous else None),
            open=field("open"), high=field("high"), low=field("low"), close=field("close"), volume=volume,
            currency=meta.get("currency"), exchange_timezone=meta.get("exchangeTimezoneName"),
            provider_timestamp=provider_time, retrieved_at=retrieved, provider_name="yahoo_finance",
            source_class=SOURCE_CLASS, data_mode="unverified_delay", data_status="unverified_delay",
            age_seconds=age, freshness=f"{age}s old" if age is not None else "provider timestamp unavailable",
            cache_status="miss", market_status=market_status, disclaimer=DISCLAIMER)
        self._quote_cache[mapped] = (now, quote); return quote

    def candles(self, instrument: Instrument) -> list[Candle]:
        mapped = yahoo_symbol(instrument); now = self.clock(); cached = self._candle_cache.get(mapped)
        if cached and now - cached[0] < self.settings.yahoo_candle_cache_seconds:
            return cached[1]
        result = self._request(instrument, interval="1d", range_="3mo")
        if "_coalesced" in result: return result["_coalesced"]
        self._validate_identity(result, mapped)
        timestamps = result.get("timestamp") or []; indicators = result.get("indicators") or {}
        quotes = indicators.get("quote") or []; adjusted = indicators.get("adjclose") or []
        if not quotes or not isinstance(quotes[0], dict): raise YahooResponseError("Yahoo Finance returned empty candle history")
        raw, adj = quotes[0], adjusted[0].get("adjclose", []) if adjusted and isinstance(adjusted[0], dict) else []
        unique: dict[datetime, Candle] = {}; current = datetime.now(timezone.utc)
        for index, timestamp in enumerate(timestamps):
            try: when = datetime.fromtimestamp(int(timestamp), timezone.utc)
            except (TypeError, ValueError, OSError): continue
            if when > current: continue
            try:
                values = {name: _number((raw.get(name) or [])[index], required=True) for name in ("open", "high", "low", "close")}
                volume = int((raw.get("volume") or [])[index])
                if volume < 0: raise YahooResponseError("Yahoo returned negative candle volume")
                adjusted_close = _number(adj[index]) if index < len(adj) else None
                unique[when] = Candle(timestamp=when, volume=volume, adjusted_close=adjusted_close, **values)
            except (IndexError, TypeError, ValueError, YahooResponseError): continue
        candles = [unique[key] for key in sorted(unique)]
        if not candles: raise YahooResponseError("Yahoo Finance returned no valid candle history")
        self._candle_cache[mapped] = (now, candles); return candles

    def quotes(self, instruments: list[Instrument]) -> list[MarketQuote]:
        # Deliberately bounded: callers request only visible/selected instruments.
        return [self.quote(item) for item in instruments[:50]]

    def status(self) -> dict[str, object]:
        return {"provider": "yahoo_finance", "access": "free_no_key", "source_class": SOURCE_CLASS,
                "data_status": "unverified_delay", "enabled": self.settings.yahoo_finance_enabled,
                "cooldown": self.clock() < self._cooldown_until, "disclaimer": DISCLAIMER}
