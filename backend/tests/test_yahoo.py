from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from app.config import get_settings
from app.schemas import Instrument
from app.services.yahoo import (DISCLAIMER, YahooFinanceProvider, YahooMappingError,
                                YahooResponseError, yahoo_symbol)


def instrument(exchange: str = "NSE", symbol: str = "M&M") -> Instrument:
    segment = f"{exchange}_EQ"
    return Instrument(instrument_key=f"{segment}|INE000A01001", exchange=exchange, segment=segment,
        symbol=symbol, name="Example Limited", isin="INE000A01001", instrument_type="EQ",
        category="stock", last_synced_at=datetime.now(timezone.utc))


def payload(symbol: str = "M&M.NS", *, price: object = 105.0, state: str = "CLOSED") -> dict:
    return {"chart": {"error": None, "result": [{"meta": {"symbol": symbol, "currency": "INR",
        "exchangeTimezoneName": "Asia/Kolkata", "regularMarketPrice": price,
        "chartPreviousClose": 100, "regularMarketTime": 1700000200, "marketState": state},
        "timestamp": [1700000000, 1700000100], "indicators": {
        "quote": [{"open": [99, 101], "high": [102, 106], "low": [98, 100],
                   "close": [101, 105], "volume": [1000, 1200]}],
        "adjclose": [{"adjclose": [100.5, 104.5]}]}}]}}


def client_for(body: dict, calls: list[int] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None: calls.append(1)
        return httpx.Response(200, json=body, request=request)
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'yahoo.db'}")
    get_settings.cache_clear(); yield; get_settings.cache_clear()


def test_mapping_nse_bse_and_special_characters() -> None:
    assert yahoo_symbol(instrument()) == "M&M.NS"
    assert yahoo_symbol(instrument("BSE", "500325")) == "500325.BO"
    assert yahoo_symbol(instrument("NSE", "BAJAJ-AUTO")) == "BAJAJ-AUTO.NS"
    with pytest.raises(YahooMappingError): yahoo_symbol(instrument("NSE", "BAD SYMBOL"))


def test_quote_normalization_closed_cache_and_attribution() -> None:
    calls: list[int] = []; provider = YahooFinanceProvider(client_for(payload(), calls))
    first = provider.quote(instrument()); second = provider.quote(instrument())
    assert first.last_price == 105 and first.percentage_change == 5
    assert first.provider_symbol == "M&M.NS" and first.market_status == "closed"
    assert first.data_mode == "unverified_delay" and first.source_class.startswith("Unofficial")
    assert first.disclaimer == DISCLAIMER and "live" not in first.data_status
    assert second.data_mode == "cached" and second.cache_status == "hit" and calls == [1]


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_quote_rejects_non_finite_price(value: float) -> None:
    token = b"NaN" if str(value) == "nan" else b"Infinity"
    raw = b'{"chart":{"error":null,"result":[{"meta":{"symbol":"M&M.NS","regularMarketPrice":' + token + b',"chartPreviousClose":100},"timestamp":[],"indicators":{"quote":[{"close":[]}]}}]}}'
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=raw, request=request)))
    with pytest.raises(YahooResponseError, match="non-finite"):
        YahooFinanceProvider(client, sleep=lambda _: None).quote(instrument())


def test_identity_mismatch_is_rejected() -> None:
    with pytest.raises(YahooMappingError, match="identity"):
        YahooFinanceProvider(client_for(payload("OTHER.NS")), sleep=lambda _: None).quote(instrument())


def test_candles_sort_dedupe_adjusted_and_cache() -> None:
    body = payload(); result = body["chart"]["result"][0]
    result["timestamp"] = [1700000100, 1700000000, 1700000100]
    for key, values in result["indicators"]["quote"][0].items(): values.append(values[0])
    result["indicators"]["adjclose"][0]["adjclose"].append(100.5)
    calls: list[int] = []; provider = YahooFinanceProvider(client_for(body, calls))
    candles = provider.candles(instrument()); again = provider.candles(instrument())
    assert len(candles) == 2 and candles == sorted(candles, key=lambda row: row.timestamp)
    assert candles[-1].adjusted_close is not None and again == candles and calls == [1]


def test_empty_history_and_bounded_retry() -> None:
    body = payload(); body["chart"]["result"][0]["indicators"]["quote"] = []
    calls: list[int] = []
    with pytest.raises(YahooResponseError, match="empty candle"):
        YahooFinanceProvider(client_for(body, calls), sleep=lambda _: None).candles(instrument())
    assert len(calls) == 1  # structurally valid empty history is not retried aggressively
