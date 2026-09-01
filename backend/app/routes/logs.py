import json

from fastapi import APIRouter

from app.database import connection
from app.schemas import AnalysisResponse
from app.schemas import AgentOutput, MarketSnapshot, Profile, Synthesis
from app.services.decision_lab import build_decision_lab

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/{user_id}", response_model=list[AnalysisResponse])
def logs(user_id: str) -> list[AnalysisResponse]:
    with connection() as conn:
        rows = conn.execute("SELECT response_json FROM analysis_logs WHERE user_id=? AND response_json IS NOT NULL ORDER BY created_at DESC, id DESC",
                            (user_id,)).fetchall()
    responses: list[AnalysisResponse] = []
    for row in rows:
        payload = json.loads(row["response_json"])
        # Preserve access to logs written before Decision Lab was introduced.
        if "decision_lab" not in payload:
            payload["decision_lab"] = build_decision_lab(
                payload["analysis_id"], MarketSnapshot.model_validate(payload["market_snapshot"]),
                Profile.model_validate(payload["profile"]),
                [AgentOutput.model_validate(agent) for agent in payload["agents"]],
                Synthesis.model_validate(payload["synthesis"]),
            ).model_dump(mode="json")
        responses.append(AnalysisResponse.model_validate(payload))
    return responses
