from fastapi import APIRouter, status

from app.database import connection
from app.schemas import DecisionInput, UserDecision

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("", response_model=UserDecision, status_code=status.HTTP_201_CREATED)
def record_decision(payload: DecisionInput) -> UserDecision:
    with connection() as conn:
        cursor = conn.execute("""INSERT INTO user_decisions
            (user_id,ticker,action,analysis_id,current_signal,confidence) VALUES (?,?,?,?,?,?)""",
            (payload.user_id, payload.ticker.upper(), payload.action, payload.analysis_id,
             payload.current_signal.value, payload.confidence))
        row = conn.execute("SELECT * FROM user_decisions WHERE id=?", (cursor.lastrowid,)).fetchone()
    return UserDecision.model_validate(dict(row))


@router.get("/{user_id}", response_model=list[UserDecision])
def decision_history(user_id: str) -> list[UserDecision]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM user_decisions WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    return [UserDecision.model_validate(dict(row)) for row in rows]
