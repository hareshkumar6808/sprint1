from fastapi import APIRouter, HTTPException, Query

from app.schemas import MarketQuote
from app.services.instruments import get_instrument
from app.services.market_data import IncompleteMarketDataError, ResilientMarketDataProvider
from app.services.upstox import UpstoxError

router = APIRouter(prefix="/market", tags=["market"])
provider = ResilientMarketDataProvider()


@router.get("/quote/{instrument_key:path}", response_model=MarketQuote)
def quote(instrument_key: str) -> MarketQuote:
    instrument = get_instrument(instrument_key)
    if not instrument:
        raise HTTPException(status_code=404, detail="Unknown instrument key")
    try:
        if provider.upstox:
            quotes = provider.upstox.quotes([instrument])
            if quotes:
                return quotes[0]
        snapshot = provider.get_instrument_snapshot(instrument)
        return MarketQuote(instrument_key=instrument.instrument_key, exchange=instrument.exchange,
            symbol=instrument.symbol, company_name=instrument.name, last_price=snapshot.current_price,
            previous_close=snapshot.previous_close,
            absolute_change=snapshot.current_price-snapshot.previous_close,
            percentage_change=(snapshot.current_price/snapshot.previous_close-1)*100,
            volume=snapshot.current_volume, provider_timestamp=snapshot.data_timestamp,
            retrieved_at=snapshot.retrieved_at or snapshot.data_timestamp, provider_name=snapshot.provider_name,
            data_mode=snapshot.data_mode, age_seconds=snapshot.age_seconds, freshness=snapshot.freshness,
            fallback_reason=snapshot.fallback_reason, market_status=snapshot.market_status)
    except IncompleteMarketDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/quotes", response_model=list[MarketQuote])
def quotes(instrument_keys: str = Query(min_length=1)) -> list[MarketQuote]:
    keys = list(dict.fromkeys(key.strip() for key in instrument_keys.split(",") if key.strip()))[:50]
    instruments = [item for key in keys if (item := get_instrument(key))]
    if provider.upstox and instruments:
        try:
            return provider.upstox.quotes(instruments)
        except UpstoxError:
            pass
    return [quote(key) for key in keys]
