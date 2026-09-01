from fastapi import APIRouter

from app.schemas import MarketSnapshot
from app.services.market_data import ResilientMarketDataProvider

router = APIRouter(prefix="/stocks", tags=["stocks"])
provider = ResilientMarketDataProvider()


@router.get("", response_model=list[MarketSnapshot])
def list_stocks() -> list[MarketSnapshot]:
    return provider.list_snapshots()
