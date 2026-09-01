from fastapi import APIRouter, HTTPException, Query

from app.schemas import CatalogueStatus, InstrumentSearchResult
from app.services.instruments import catalogue_status, search_instruments, sync_catalogue

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/search", response_model=list[InstrumentSearchResult])
def search(q: str = "", exchange: str | None = Query(default=None, pattern="^(NSE|BSE)$"),
           limit: int = Query(default=20, ge=1, le=50)) -> list[InstrumentSearchResult]:
    return search_instruments(q, exchange, limit)


@router.get("/status", response_model=CatalogueStatus)
def status() -> CatalogueStatus:
    return catalogue_status()


@router.post("/refresh", response_model=CatalogueStatus)
def refresh(force: bool = False) -> CatalogueStatus:
    result = sync_catalogue(force=force)
    if result.status == "failed" and not result.instrument_count:
        raise HTTPException(status_code=503, detail=result.error or "Instrument refresh failed")
    return result
