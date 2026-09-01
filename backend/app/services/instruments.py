"""Provider-independent, persistent NSE/BSE equity catalogue."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.database import connection
from app.schemas import CatalogueStatus, Instrument, InstrumentSearchResult

FIXTURE = Path(__file__).parent.parent / "data" / "instruments_fixture.json"


def parse_instruments(records: list[dict[str, Any]], synced_at: datetime | None = None) -> list[Instrument]:
    timestamp = synced_at or datetime.now(timezone.utc)
    parsed: list[Instrument] = []
    for row in records:
        if row.get("segment") not in {"NSE_EQ", "BSE_EQ"} or row.get("instrument_type") != "EQ":
            continue
        try:
            parsed.append(Instrument(instrument_key=str(row["instrument_key"]), exchange=row["exchange"],
                segment=row["segment"], symbol=str(row["trading_symbol"]).upper(), name=str(row["name"]),
                isin=row.get("isin"), tick_size=row.get("tick_size"), lot_size=row.get("lot_size"),
                instrument_type=str(row["instrument_type"]), last_synced_at=timestamp))
        except (KeyError, TypeError, ValueError):
            continue
    return parsed


def upsert_instruments(items: list[Instrument]) -> int:
    if not items:
        return 0
    with connection() as conn:
        conn.executemany("""INSERT INTO instruments
          (instrument_key,exchange,segment,symbol,name,isin,tick_size,lot_size,instrument_type,last_synced_at)
          VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(instrument_key) DO UPDATE SET
          exchange=excluded.exchange,segment=excluded.segment,symbol=excluded.symbol,name=excluded.name,
          isin=excluded.isin,tick_size=excluded.tick_size,lot_size=excluded.lot_size,
          instrument_type=excluded.instrument_type,last_synced_at=excluded.last_synced_at""",
          [(item.instrument_key, item.exchange, item.segment, item.symbol, item.name, item.isin,
            item.tick_size, item.lot_size, item.instrument_type, item.last_synced_at.isoformat()) for item in items])
    return len(items)


def seed_fixture_if_empty() -> None:
    with connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
    if count == 0:
        upsert_instruments(parse_instruments(json.loads(FIXTURE.read_text())))


def catalogue_status() -> CatalogueStatus:
    with connection() as conn:
        row = conn.execute("SELECT * FROM catalogue_sync WHERE provider='upstox'").fetchone()
        count = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
    if not row:
        return CatalogueStatus(provider="upstox", status="cached" if count else "never", instrument_count=count)
    data = dict(row); data["provider"] = "upstox"; data["instrument_count"] = count
    return CatalogueStatus.model_validate(data)


def sync_catalogue(force: bool = False, client: httpx.Client | None = None) -> CatalogueStatus:
    settings = get_settings(); current = catalogue_status(); now = datetime.now(timezone.utc)
    if (not force and current.last_success_at and
            now - current.last_success_at < timedelta(hours=settings.instrument_refresh_hours)):
        return current.model_copy(update={"status": "cached"})
    owned = client is None
    remote = client or httpx.Client(timeout=settings.market_request_timeout_seconds, follow_redirects=True)
    try:
        response = remote.get(settings.upstox_instrument_master_url, headers={"Accept": "application/json"})
        response.raise_for_status(); payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Instrument master was not a JSON list")
        items = parse_instruments(payload, now)
        if not items:
            raise ValueError("Instrument master contained no supported NSE/BSE equities")
        upsert_instruments(items)
        status, error, success = "success", None, now.isoformat()
    except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError) as exc:
        status, error, success = "failed", f"{type(exc).__name__}: {exc}", current.last_success_at.isoformat() if current.last_success_at else None
    finally:
        if owned:
            remote.close()
    with connection() as conn:
        conn.execute("""INSERT INTO catalogue_sync(provider,status,last_attempt_at,last_success_at,instrument_count,error)
          VALUES('upstox',?,?,?,?,?) ON CONFLICT(provider) DO UPDATE SET status=excluded.status,
          last_attempt_at=excluded.last_attempt_at,last_success_at=excluded.last_success_at,
          instrument_count=excluded.instrument_count,error=excluded.error""",
          (status, now.isoformat(), success, len(items) if status == "success" else current.instrument_count, error))
    result = catalogue_status()
    return result.model_copy(update={"status": "cached"}) if status == "failed" and result.instrument_count else result


def search_instruments(query: str, exchange: str | None = None, limit: int = 20) -> list[InstrumentSearchResult]:
    term = query.strip().upper()
    if not term:
        return []
    params: list[object] = [term, f"{term}%", f"%{term}%", f"%{term}%"]
    exchange_sql = ""
    if exchange:
        exchange_sql = " AND exchange=?"; params.append(exchange.upper())
    params.append(max(1, min(limit, 50)))
    with connection() as conn:
        rows = conn.execute(f"""SELECT * FROM instruments WHERE
          (UPPER(symbol)=? OR UPPER(symbol) LIKE ? OR UPPER(name) LIKE ? OR UPPER(isin) LIKE ?)
          {exchange_sql} ORDER BY CASE WHEN UPPER(symbol)=? THEN 0 WHEN UPPER(symbol) LIKE ? THEN 1 ELSE 2 END,
          LENGTH(symbol), name LIMIT ?""", [*params[:-1], term, f"{term}%", params[-1]]).fetchall()
    return [InstrumentSearchResult(instrument_key=row["instrument_key"], exchange=row["exchange"],
        symbol=row["symbol"], name=row["name"], isin=row["isin"], instrument_type=row["instrument_type"]) for row in rows]


def get_instrument(instrument_key: str) -> Instrument | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM instruments WHERE instrument_key=?", (instrument_key,)).fetchone()
    return Instrument.model_validate(dict(row)) if row else None


def find_by_symbol(symbol: str) -> Instrument | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM instruments WHERE UPPER(symbol)=? ORDER BY exchange='NSE' DESC LIMIT 1",
                           (symbol.upper(),)).fetchone()
    return Instrument.model_validate(dict(row)) if row else None
