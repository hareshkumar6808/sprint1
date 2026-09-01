import re
import base64
import io
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.database import connection
from app.config import get_settings
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
    content: str | None = None
    content_base64: str | None = None
    media_type: str = "text/plain"
    publisher: str | None = None
    url: str | None = None
    simulated: bool = False

    @model_validator(mode="after")
    def require_content(self) -> "DocumentInput":
        if not self.content and not self.content_base64:
            raise ValueError("content or content_base64 is required")
        if self.media_type not in {"text/plain", "application/pdf"}:
            raise ValueError("Only text/plain and application/pdf are supported")
        return self


def _text(payload: DocumentInput) -> str:
    settings = get_settings()
    if payload.content is not None:
        raw = payload.content.encode("utf-8"); text = payload.content
    else:
        try: raw = base64.b64decode(payload.content_base64 or "", validate=True)
        except ValueError as exc: raise HTTPException(422, "content_base64 is invalid") from exc
        if payload.media_type == "application/pdf":
            try:
                from pypdf import PdfReader
                text = "\n\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)
            except ImportError as exc: raise HTTPException(503, "PDF support requires pypdf") from exc
            except Exception as exc: raise HTTPException(422, "PDF could not be safely parsed") from exc
        else:
            try: text = raw.decode("utf-8")
            except UnicodeDecodeError as exc: raise HTTPException(422, "Text document must be UTF-8") from exc
    if len(raw) > settings.document_max_bytes:
        raise HTTPException(413, f"Document exceeds {settings.document_max_bytes} byte limit")
    normalized = re.sub(r"[ \t]+", " ", text).replace("\x00", "").strip()
    if len(normalized) < 20: raise HTTPException(422, "Document has insufficient extractable text")
    return normalized


@router.post("", status_code=201)
def ingest(payload: DocumentInput) -> dict[str, object]:
    instrument = get_instrument(payload.instrument_key)
    if not instrument or instrument.symbol != payload.symbol.upper():
        raise HTTPException(status_code=400, detail="Instrument key and symbol do not match the catalogue")
    safe_symbol = re.sub(r"[^A-Z0-9]+", "_", instrument.symbol)
    safe_key = re.sub(r"[^A-Za-z0-9]+", "_", instrument.instrument_key)
    INGESTED.mkdir(parents=True, exist_ok=True)
    path = INGESTED / f"{safe_symbol}_{safe_key}_{payload.source_date.isoformat()}.txt"
    path.write_text(_text(payload))
    with connection() as conn:
        cursor = conn.execute("""INSERT INTO instrument_documents
          (instrument_key,symbol,company_name,title,document_type,source_date,attribution,local_path)
          VALUES(?,?,?,?,?,?,?,?)""", (instrument.instrument_key, instrument.symbol, payload.company_name,
          payload.title, payload.document_type, payload.source_date.isoformat(), payload.attribution, str(path)))
    return {"id": cursor.lastrowid, "instrument_key": instrument.instrument_key, "title": payload.title}
