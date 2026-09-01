import json
from pathlib import Path

from fastapi import APIRouter

from app.schemas import MarketSnapshot

router = APIRouter(prefix="/stocks", tags=["stocks"])
DATA_FILE = Path(__file__).parent.parent / "data" / "market_data.json"


@router.get("", response_model=list[MarketSnapshot])
def list_stocks() -> list[MarketSnapshot]:
    return [MarketSnapshot.model_validate(item) for item in json.loads(DATA_FILE.read_text())]

