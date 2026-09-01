import json

from fastapi import APIRouter

from app.database import connection
from app.schemas import AnalysisResponse

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/{user_id}", response_model=list[AnalysisResponse])
def logs(user_id: str) -> list[AnalysisResponse]:
    with connection() as conn:
        rows = conn.execute("SELECT response_json FROM analysis_logs WHERE user_id=? AND response_json IS NOT NULL ORDER BY created_at DESC, id DESC",
                            (user_id,)).fetchall()
    return [AnalysisResponse.model_validate(json.loads(row["response_json"])) for row in rows]
