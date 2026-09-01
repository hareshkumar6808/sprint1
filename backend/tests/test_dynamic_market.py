import gzip
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schemas import Candle, MarketQuote
from app.services.instruments import (get_instrument, parse_instruments, search_instruments,
                                      sync_catalogue, upsert_instruments,
                                      decode_instrument_master, InstrumentMasterError)
from app.services.market_data import snapshot_from_market_data
from app.services.upstox import (UpstoxAuthenticationError, UpstoxProvider,
                                 UpstoxRateLimitError)
from app.services.retrieval import FilingRetriever

MASTER = [
    {"segment": "NSE_EQ", "name": "ACME INDUSTRIES LTD", "exchange": "NSE", "isin": "INE000X01001",
     "instrument_type": "EQ", "instrument_key": "NSE_EQ|INE000X01001", "lot_size": 1,
     "tick_size": 5, "trading_symbol": "ACME"},
    {"segment": "BSE_EQ", "name": "ACME INDUSTRIES LTD", "exchange": "BSE", "isin": "INE000X01001",
     "instrument_type": "EQ", "instrument_key": "BSE_EQ|INE000X01001", "lot_size": 1,
     "tick_size": 5, "trading_symbol": "500001"},
    {"segment": "NSE_FO", "name": "ACME INDUSTRIES LTD", "exchange": "NSE", "instrument_type": "FUT",
     "instrument_key": "NSE_FO|1", "trading_symbol": "ACME FUT"},
]


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'dynamic.db'}")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def mock_client(status: int, payload: object, counter: list[int] | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if counter is not None: counter.append(1)
        return httpx.Response(status, json=payload, request=request)
    return httpx.Client(transport=httpx.MockTransport(handler))


def bytes_client(content: bytes, headers: dict[str, str] | None = None, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=content, headers=headers, request=request)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_master_filter_upsert_search_ranking_and_exchange(client: TestClient) -> None:
    parsed = parse_instruments(MASTER)
    assert len(parsed) == 2 and {item.exchange for item in parsed} == {"NSE", "BSE"}
    assert upsert_instruments(parsed) == 2 and upsert_instruments(parsed) == 2
    exact = search_instruments("ACME")
    assert exact[0].symbol == "ACME"
    assert len([item for item in exact if item.instrument_key == "NSE_EQ|INE000X01001"]) == 1
    assert all(item.exchange == "BSE" for item in search_instruments("ACME", "BSE"))
    assert search_instruments("") == []


def test_catalogue_sync_mock_and_cached_failure(client: TestClient) -> None:
    first = sync_catalogue(force=True, client=mock_client(200, MASTER))
    assert first.status == "success" and first.instrument_count >= 2 and first.last_success_at
    failed = sync_catalogue(force=True, client=mock_client(503, {"error": "down"}))
    assert failed.status == "cached" and failed.instrument_count == first.instrument_count and failed.error
    assert failed.last_success_at == first.last_success_at


def test_instrument_master_decodes_gzip_plain_magic_and_http_decoded_bytes() -> None:
    plain = json.dumps(MASTER).encode()
    compressed = gzip.compress(plain)
    assert len(decode_instrument_master(compressed)) == len(MASTER)
    assert len(decode_instrument_master(compressed, None)) == len(MASTER)
    # A client may transparently decompress content while retaining gzip metadata.
    assert len(decode_instrument_master(plain, "gzip")) == len(MASTER)
    assert len(decode_instrument_master(plain)) == len(MASTER)


@pytest.mark.parametrize("content, message", [
    (b"\x1f\x8bcorrupt", "gzip payload is invalid"),
    (gzip.compress(b"not-json"), "invalid JSON"),
    (gzip.compress(b"\xff\xfe"), "not valid UTF-8"),
    (b"", "response was empty"),
    (b'{"records": []}', "top-level list"),
])
def test_instrument_master_safe_decode_errors(content: bytes, message: str) -> None:
    with pytest.raises(InstrumentMasterError, match=message):
        decode_instrument_master(content)


def test_gzip_refresh_sets_success_and_repeated_refresh_does_not_duplicate(client: TestClient) -> None:
    compressed = gzip.compress(json.dumps(MASTER).encode())
    first = sync_catalogue(force=True, client=bytes_client(compressed))
    second = sync_catalogue(force=True, client=bytes_client(compressed, {"content-encoding": "gzip"}))
    assert first.status == second.status == "success"
    assert first.last_success_at and second.last_success_at
    assert first.instrument_count == second.instrument_count
    assert len(search_instruments("ACME")) == 2
    assert not search_instruments("ACME FUT")


def quote_payload() -> dict[str, object]:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {"status": "success", "data": {"NSE_EQ:ACME": {"instrument_token": "NSE_EQ|INE000X01001",
        "symbol": "ACME", "last_price": 105.0, "volume": 12000, "net_change": 5.0,
        "timestamp": str(now_ms), "ohlc": {"open": 101, "high": 106, "low": 99, "close": 100}}}}


def test_live_quote_adapter_cache_auth_and_rate_limit(client: TestClient) -> None:
    upsert_instruments(parse_instruments(MASTER)); instrument = get_instrument("NSE_EQ|INE000X01001")
    assert instrument
    calls: list[int] = []; provider = UpstoxProvider("placeholder", mock_client(200, quote_payload(), calls))
    first = provider.quotes([instrument])[0]; second = provider.quotes([instrument])[0]
    assert first.data_mode == "live" and first.percentage_change == 5
    assert second.data_mode == "cached" and len(calls) == 1
    with pytest.raises(UpstoxAuthenticationError):
        UpstoxProvider("bad", mock_client(401, {})).quotes([instrument])
    with pytest.raises(UpstoxRateLimitError):
        UpstoxProvider("limited", mock_client(429, {})).quotes([instrument])


def test_simulated_quote_fallback_is_explicit(client: TestClient) -> None:
    response = client.get("/api/v1/market/quote/NSE_EQ%7CINE002A01018")
    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "simulated" and body["provider_name"] == "local_simulated_fixture"
    assert body["fallback_reason"] == "Upstox live mode is not configured"


def test_candle_normalization_and_dynamic_indicators(client: TestClient) -> None:
    upsert_instruments(parse_instruments(MASTER)); instrument = get_instrument("NSE_EQ|INE000X01001")
    assert instrument
    start = datetime.now(timezone.utc) - timedelta(days=35)
    rows = [[(start + timedelta(days=i)).isoformat(), 100+i, 102+i, 99+i, 101+i, 1000+i, 0] for i in range(30)]
    rows.extend([rows[-1], ["bad"]])
    provider = UpstoxProvider("placeholder", mock_client(200, {"status": "success", "data": {"candles": rows}}))
    candles = provider.candles(instrument.instrument_key)
    assert len(candles) == 30 and candles == sorted(candles, key=lambda item: item.timestamp)
    quote = MarketQuote(instrument_key=instrument.instrument_key, exchange="NSE", symbol="ACME",
        company_name=instrument.name, last_price=130, previous_close=129, retrieved_at=datetime.now(timezone.utc),
        provider_name="upstox", data_mode="live", freshness="exchange snapshot")
    snapshot = snapshot_from_market_data(instrument, quote, candles)
    assert snapshot.five_day_return is not None and snapshot.twenty_day_return is not None and snapshot.rsi is not None
    short = snapshot_from_market_data(instrument, quote, candles[:3])
    assert short.five_day_return is None and short.rsi is None and short.indicator_warnings


def test_dynamic_search_profile_and_missing_documents_degrade(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    upsert_instruments(parse_instruments(MASTER))
    profile = {"user_id":"dynamic-user","risk_profile":"moderate","investment_horizon_years":8,
        "maximum_volatility":25,"portfolio":[{"instrument_key":"NSE_EQ|INE000X01001","symbol":"ACME","weight":100}],
        "watchlist":["NSE_EQ|INE000X01001"],"interaction_history":[]}
    assert client.post("/api/v1/profiles", json=profile).status_code == 201
    candles = [Candle(timestamp=datetime.now(timezone.utc)-timedelta(days=30-i), open=100+i,
        high=102+i, low=99+i, close=101+i, volume=1000+i) for i in range(30)]
    instrument = get_instrument("NSE_EQ|INE000X01001"); assert instrument
    quote = MarketQuote(instrument_key=instrument.instrument_key, exchange="NSE", symbol="ACME",
        company_name=instrument.name,last_price=130,previous_close=129,retrieved_at=datetime.now(timezone.utc),
        provider_name="upstox",data_mode="live",freshness="mock")
    snapshot = snapshot_from_market_data(instrument, quote, candles)
    monkeypatch.setattr("app.routes.analysis.provider.get_instrument_snapshot", lambda _: snapshot)
    result = client.post("/api/v1/analyze", json={"user_id":"dynamic-user","symbol":"ACME",
        "instrument_key":instrument.instrument_key})
    assert result.status_code == 200
    body = result.json(); fundamental = next(item for item in body["agents"] if item["agent"] == "fundamental")
    assert body["market_snapshot"]["provider_name"] == "upstox"
    assert fundamental["status"] == "unavailable" and not fundamental["sources"]
    assert body["decision_lab"]["investigation_id"].startswith("INV-ACME-")
    stored = client.get("/api/v1/profiles/dynamic-user").json()
    assert stored["watchlist"] == [instrument.instrument_key]
    assert stored["portfolio"][0]["instrument_key"] == instrument.instrument_key


def test_document_ingestion_and_no_cross_company_leakage(client: TestClient, tmp_path: Path,
                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    upsert_instruments(parse_instruments(MASTER))
    monkeypatch.setattr("app.routes.documents.INGESTED", tmp_path)
    payload = {"instrument_key":"NSE_EQ|INE000X01001","symbol":"ACME","company_name":"ACME INDUSTRIES LTD",
        "title":"ACME Annual Report","source_date":"2026-08-01","document_type":"annual_report",
        "attribution":"Locally supplied by administrator",
        "content":"ACME revenue growth improved while liquidity remained adequate. This document belongs only to ACME."}
    response = client.post("/api/v1/documents", json=payload)
    assert response.status_code == 201
    (tmp_path / "TCS_Q1.txt").write_text("TCS revenue and contracts only; this must not leak into ACME evidence.")
    retriever = FilingRetriever(tmp_path, force_tfidf=True, vector_store=tmp_path / "vectors.json")
    acme = retriever.retrieve("ACME", "revenue growth", limit=5)
    assert acme and all(chunk.document.startswith("ACME_") for chunk in acme)
    assert not any("TCS" in chunk.text for chunk in acme)
