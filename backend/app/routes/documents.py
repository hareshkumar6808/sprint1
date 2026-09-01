import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import connection
from app.services.instruments import get_instrument

router = APIRouter(prefix="/documents", tags=["documents"])
INGESTED = Path(__file__).parent.parent / "data" / "filings" / "ingested"


class DocumentInput(BaseModel):
    instrument_key: str
    symbol: str
    company_name: str
    title: str
    source_date: date
    document_type: str = Field(min_length=1)
    attribution: str = Field(min_length=1)
    content: str = Field(min_length=20)


@router.post("", status_code=201)
def ingest(payload: DocumentInput) -> dict[str, object]:
    instrument = get_instrument(payload.instrument_key)
    if not instrument or instrument.symbol != payload.symbol.upper():
        raise HTTPException(status_code=400, detail="Instrument key and symbol do not match the catalogue")
    safe_symbol = re.sub(r"[^A-Z0-9]+", "_", instrument.symbol)
    safe_key = re.sub(r"[^A-Za-z0-9]+", "_", instrument.instrument_key)
    INGESTED.mkdir(parents=True, exist_ok=True)
    path = INGESTED / f"{safe_symbol}_{safe_key}_{payload.source_date.isoformat()}.txt"
    path.write_text(payload.content)
    with connection() as conn:
        cursor = conn.execute("""INSERT INTO instrument_documents
          (instrument_key,symbol,company_name,title,document_type,source_date,attribution,local_path)
          VALUES(?,?,?,?,?,?,?,?)""", (instrument.instrument_key, instrument.symbol, payload.company_name,
          payload.title, payload.document_type, payload.source_date.isoformat(), payload.attribution, str(path)))
    return {"id": cursor.lastrowid, "instrument_key": instrument.instrument_key, "title": payload.title}
