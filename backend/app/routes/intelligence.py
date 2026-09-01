"""Additive A-Z intelligence, simulation, journal, event, and reliability APIs."""
import json
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import connection, encode_json
from app.schemas import AnalysisResponse

router = APIRouter(tags=["intelligence"])


class JournalInput(BaseModel):
    user_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    thesis: str = Field(min_length=1, max_length=4000)
    action: Literal["BUY", "SELL", "WATCH", "IGNORE", "INVESTIGATE", "thesis_recorded"]
    expected_holding_period: str | None = None
    expected_catalyst: str | None = None
    reconsideration_condition: str | None = None
    confidence: int = Field(ge=0, le=100)
    notes: str | None = Field(default=None, max_length=4000)


class ShockInput(BaseModel):
    scenario: Literal["nifty_decline", "sector_decline", "oil_increase", "inr_depreciation", "interest_rate_increase", "user_defined"]
    shock_percent: float = Field(ge=-100, le=100)
    holdings: list[dict[str, Any]] = Field(default_factory=list)


class PortfolioSimulationInput(BaseModel):
    holdings: list[dict[str, Any]]
    proposed_symbol: str
    proposed_allocation: float = Field(ge=0, le=100)


def _analysis(analysis_id: str) -> AnalysisResponse:
    with connection() as conn:
        row = conn.execute("SELECT response_json FROM analysis_logs WHERE analysis_id=?", (analysis_id,)).fetchone()
    if row is None or not row["response_json"]:
        raise HTTPException(404, "Investigation not found")
    return AnalysisResponse.model_validate_json(row["response_json"])


@router.get("/system/status")
def system_status() -> dict[str, Any]:
    settings = get_settings()
    xai_ready = settings.llm_provider == "xai" and bool(settings.xai_api_key and settings.xai_model)
    return {"service": "finsync-intelligence-api", "version": settings.version,
            "market_provider": settings.market_data_provider, "market_mode": settings.market_data_mode,
            "llm_provider": settings.llm_provider, "llm_runtime": "xai" if xai_ready else "disabled",
            "xai_configured": xai_ready, "semantic_retrieval_requested": settings.semantic_retrieval_enabled,
            "secrets_exposed": False}


@router.get("/investigations")
def investigations(user_id: str, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> dict[str, Any]:
    with connection() as conn:
        total = conn.execute("SELECT count(*) FROM analysis_logs WHERE user_id=?", (user_id,)).fetchone()[0]
        rows = conn.execute("SELECT response_json FROM analysis_logs WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (user_id, limit, offset)).fetchall()
    items = [AnalysisResponse.model_validate_json(row[0]).model_dump(mode="json") for row in rows if row[0]]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/investigations/{analysis_id}", response_model=AnalysisResponse)
def investigation_detail(analysis_id: str) -> AnalysisResponse:
    return _analysis(analysis_id)


@router.get("/investigations/{analysis_id}/committee")
def committee_detail(analysis_id: str) -> dict[str, Any]:
    result = _analysis(analysis_id)
    return {"investigation_id": result.decision_lab.investigation_id,
            "committee": result.decision_lab.committee, "analytical_units": result.analytical_units,
            "weights": result.synthesis_weights, "regime": result.regime}


@router.post("/investigations/{analysis_id}/source-removal")
def source_removal(analysis_id: str, source_id: str) -> dict[str, Any]:
    result = _analysis(analysis_id)
    matched = [source for source in result.sources if source.source_id == source_id or source.chunk_id == source_id or source.document == source_id]
    if not matched:
        raise HTTPException(404, "Source does not belong to this investigation")
    affected = [agent for agent in result.agents if source_id in agent.evidence_ids or any(source in matched for source in agent.sources)]
    penalty = min(result.synthesis.confidence, max(5, round(sum(agent.confidence for agent in affected) / max(1, len(result.agents)))))
    return {"source_id": source_id, "affected_agents": [agent.agent for agent in affected],
            "confidence_before": result.synthesis.confidence,
            "confidence_after": max(0, result.synthesis.confidence - penalty),
            "conclusion_robust": penalty <= 12,
            "limitations": ["Deterministic sensitivity test; remaining evidence is not reinterpreted by an LLM."]}


@router.post("/investigations/{analysis_id}/confidence-stress")
def confidence_stress(analysis_id: str, freshness_penalty: int = Query(10, ge=0, le=100),
                      missing_source_penalty: int = Query(10, ge=0, le=100)) -> dict[str, Any]:
    result = _analysis(analysis_id)
    stressed = max(0, result.synthesis.confidence - freshness_penalty - missing_source_penalty)
    return {"normal_confidence": result.synthesis.confidence, "stressed_confidence": stressed,
            "penalties": {"freshness": freshness_penalty, "missing_source": missing_source_penalty}}


@router.post("/portfolio/simulate")
def portfolio_simulate(payload: PortfolioSimulationInput) -> dict[str, Any]:
    weights = [max(0.0, float(item.get("weight", item.get("allocation", 0)))) for item in payload.holdings]
    total = sum(weights)
    if total <= 0:
        raise HTTPException(422, "Holdings require positive allocation weights")
    normalized = [weight / total * 100 for weight in weights]
    before_top = max(normalized)
    scaled = [weight * (100 - payload.proposed_allocation) / 100 for weight in normalized]
    after = [*scaled, payload.proposed_allocation]
    return {"before": {"allocation": normalized, "top_holding_concentration": round(before_top, 2),
                        "diversification": round(100 - before_top, 2)},
            "after": {"allocation": after, "top_holding_concentration": round(max(after), 2),
                       "diversification": round(100 - max(after), 2)},
            "risk": "insufficient_data", "suitability": "insufficient_data",
            "assumptions": ["Allocation-only simulation; correlations, sectors, and volatility were not supplied."]}


@router.post("/portfolio/shock")
def portfolio_shock(payload: ShockInput) -> dict[str, Any]:
    total = sum(max(0.0, float(item.get("value", 0))) for item in payload.holdings)
    if total <= 0:
        raise HTTPException(422, "Holdings require positive values")
    exposed = sum(max(0.0, float(item.get("value", 0))) for item in payload.holdings if item.get("exposed", True))
    impact = exposed * payload.shock_percent / 100
    return {"scenario": payload.scenario, "portfolio_value_before": total,
            "estimated_value_after": round(total + impact, 2), "estimated_impact": round(impact, 2),
            "assumptions": ["User-supplied shock is applied linearly only to holdings marked exposed.",
                            "No unsupported asset sensitivity or correlation is invented."]}


@router.get("/time-travel/{symbol}")
def time_travel(symbol: str, as_of: datetime) -> dict[str, Any]:
    with connection() as conn:
        rows = conn.execute("SELECT response_json,created_at FROM analysis_logs WHERE symbol=? AND created_at<=? ORDER BY created_at DESC",
                            (symbol.upper(), as_of.isoformat())).fetchall()
    return {"symbol": symbol.upper(), "as_of": as_of, "items": [json.loads(row[0]) for row in rows if row[0]],
            "look_ahead_excluded": True}


@router.post("/journals", status_code=201)
def create_journal(payload: JournalInput) -> dict[str, Any]:
    with connection() as conn:
        cursor = conn.execute("""INSERT INTO journals
          (user_id,symbol,thesis,action,holding_period,catalyst,reconsideration_condition,confidence,notes)
          VALUES (?,?,?,?,?,?,?,?,?)""", (payload.user_id, payload.symbol.upper(), payload.thesis, payload.action,
          payload.expected_holding_period, payload.expected_catalyst, payload.reconsideration_condition,
          payload.confidence, payload.notes))
        row = conn.execute("SELECT * FROM journals WHERE id=?", (cursor.lastrowid,)).fetchone()
    return dict(row)


@router.get("/journals/{user_id}")
def journals(user_id: str, limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    with connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM journals WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))]


@router.get("/behavior/{user_id}")
def behavior(user_id: str) -> dict[str, Any]:
    with connection() as conn:
        rows = conn.execute("SELECT id,action,ticker,created_at FROM user_decisions WHERE user_id=? ORDER BY id", (user_id,)).fetchall()
    if len(rows) < 5:
        return {"status": "insufficient_history", "sample_size": len(rows), "patterns": [],
                "minimum_sample": 5, "supporting_event_ids": [], "confidence": 0}
    actions = [row["action"] for row in rows]
    patterns = ["overtrading"] if len(rows) >= 10 else []
    return {"status": "evaluated", "sample_size": len(rows), "patterns": patterns,
            "supporting_event_ids": [row["id"] for row in rows] if patterns else [],
            "confidence": min(80, len(rows) * 5), "observed_actions": actions}


@router.get("/events")
def events(symbol: str | None = None, limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    with connection() as conn:
        if symbol:
            rows = conn.execute("SELECT * FROM events WHERE symbol=? ORDER BY occurred_at DESC LIMIT ?", (symbol.upper(), limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM events ORDER BY occurred_at DESC LIMIT ?", (limit,)).fetchall()
    return [{**dict(row), "evidence": json.loads(row["evidence_json"])} for row in rows]


@router.get("/predictions")
def predictions(symbol: str | None = None, limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    with connection() as conn:
        query = "SELECT * FROM predictions" + (" WHERE symbol=?" if symbol else "") + " ORDER BY id DESC LIMIT ?"
        params: tuple[Any, ...] = (symbol.upper(), limit) if symbol else (limit,)
        return [dict(row) for row in conn.execute(query, params)]


@router.get("/agent-performance")
def agent_performance() -> dict[str, Any]:
    settings = get_settings()
    with connection() as conn:
        evaluated = conn.execute("SELECT count(*) FROM predictions WHERE direction_correct IS NOT NULL").fetchone()[0]
        correct = conn.execute("SELECT count(*) FROM predictions WHERE direction_correct=1").fetchone()[0]
    if evaluated < settings.reliability_min_samples:
        return {"status": "insufficient_evaluated_history", "evaluated": evaluated, "correct": correct,
                "minimum_sample": settings.reliability_min_samples, "accuracy_percent": None}
    return {"status": "evaluated", "evaluated": evaluated, "correct": correct,
            "minimum_sample": settings.reliability_min_samples, "accuracy_percent": round(correct / evaluated * 100, 2)}
