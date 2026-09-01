import asyncio
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schemas import AgentOutput, AgentStatus, Classification
from app.services.llm_provider import LLMProvider


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'az.db'}")
    monkeypatch.setenv("MARKET_DATA_MODE", "simulated")
    get_settings.cache_clear()
    with TestClient(app) as value: yield value
    get_settings.cache_clear()


def create_profile(client: TestClient, user: str = "az-user") -> None:
    response = client.post("/api/v1/profiles", json={"user_id": user, "risk_profile": "moderate",
        "investment_horizon_years": 8, "maximum_volatility": 25,
        "portfolio": [{"symbol": "TCS", "weight": 70}, {"symbol": "RELIANCE", "weight": 30}],
        "watchlist": ["TCS"], "interaction_history": [], "name": "A Z", "style": "quality"})
    assert response.status_code == 201 and response.json()["name"] == "A Z"


def test_expanded_committee_persistence_events_and_prediction_dedup(client: TestClient) -> None:
    create_profile(client)
    first = client.post("/api/v1/analyze", json={"user_id": "az-user", "symbol": "RELIANCE"})
    second = client.post("/api/v1/analyze", json={"user_id": "az-user", "symbol": "RELIANCE"})
    assert first.status_code == second.status_code == 200
    body = first.json()
    assert len(body["agents"]) == 4 and len(body["analytical_units"]) == 12
    assert {item["agent"] for item in body["analytical_units"]} >= {"regulatory", "macro_regime", "portfolio_risk", "devils_advocate", "missing_information", "evidence_verification", "committee", "synthesis"}
    assert body["regime"] == "unknown" and round(sum(body["synthesis_weights"].values()), 3) == 1
    assert len(client.get("/api/v1/events?symbol=RELIANCE").json()) == 1
    assert len(client.get("/api/v1/predictions?symbol=RELIANCE").json()) == 2
    performance = client.get("/api/v1/agent-performance").json()
    assert performance["status"] == "insufficient_evaluated_history" and performance["accuracy_percent"] is None


def test_decision_services_journal_behavior_and_no_lookahead(client: TestClient) -> None:
    create_profile(client)
    analysis = client.post("/api/v1/analyze", json={"user_id": "az-user", "symbol": "TCS"}).json()
    analysis_id = analysis["analysis_id"]
    assert client.get(f"/api/v1/investigations/{analysis_id}/committee").status_code == 200
    stressed = client.post(f"/api/v1/investigations/{analysis_id}/confidence-stress?freshness_penalty=8&missing_source_penalty=7").json()
    assert stressed["stressed_confidence"] <= stressed["normal_confidence"]
    source = next(item for item in analysis["sources"] if item.get("source_id"))
    removed = client.post(f"/api/v1/investigations/{analysis_id}/source-removal", params={"source_id": source["source_id"]}).json()
    assert removed["confidence_after"] <= removed["confidence_before"]
    journal = client.post("/api/v1/journals", json={"user_id": "az-user", "symbol": "TCS", "thesis": "Monitor cited risks.",
        "action": "WATCH", "confidence": 55}).json()
    assert journal["id"] and client.get("/api/v1/journals/az-user").json()[0]["thesis"] == "Monitor cited risks."
    assert client.get("/api/v1/behavior/az-user").json()["status"] == "insufficient_history"
    travel = client.get("/api/v1/time-travel/TCS", params={"as_of": datetime.now(timezone.utc).isoformat()}).json()
    assert travel["look_ahead_excluded"] is True


def test_portfolio_and_shock_simulations_disclose_assumptions(client: TestClient) -> None:
    simulation = client.post("/api/v1/portfolio/simulate", json={"holdings": [{"symbol": "TCS", "weight": 100}],
        "proposed_symbol": "RELIANCE", "proposed_allocation": 20}).json()
    assert simulation["after"]["top_holding_concentration"] == 80
    assert simulation["risk"] == "insufficient_data" and simulation["assumptions"]
    shock = client.post("/api/v1/portfolio/shock", json={"scenario": "user_defined", "shock_percent": -10,
        "holdings": [{"symbol": "TCS", "value": 100000, "exposed": True}]}).json()
    assert shock["estimated_value_after"] == 90000 and shock["assumptions"]


class FakeResponse:
    def __init__(self, status: int, body: dict): self.status_code, self._body = status, body
    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.x.ai/v1/chat/completions")
            raise httpx.HTTPStatusError("failure", request=request, response=httpx.Response(self.status_code, request=request))
    def json(self) -> dict: return self._body


class FakeClient:
    def __init__(self, response: FakeResponse): self.response = response
    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass
    async def post(self, *_, **__): return self.response


def test_xai_structured_success_and_malformed_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "xai"); monkeypatch.setenv("XAI_API_KEY", "placeholder"); monkeypatch.setenv("XAI_MODEL", "test-model")
    get_settings.cache_clear(); LLMProvider._cooldown_until = 0; LLMProvider._calls_by_day.clear()
    deterministic = AgentOutput(agent="technical", status=AgentStatus.completed, classification=Classification.bullish,
        confidence=70, summary="bounded", evidence=["claim"], evidence_ids=["e1"], latency_ms=1)
    valid = deterministic.model_dump_json()
    monkeypatch.setattr("app.services.llm_provider.httpx.AsyncClient", lambda **_: FakeClient(FakeResponse(200,
        {"model": "test-model", "usage": {"total_tokens": 10}, "choices": [{"message": {"content": valid}}]})))
    result = asyncio.run(LLMProvider().refine("technical", deterministic))
    assert result.runtime_mode == "xai" and result.model == "test-model"
    monkeypatch.setattr("app.services.llm_provider.httpx.AsyncClient", lambda **_: FakeClient(FakeResponse(200,
        {"choices": [{"message": {"content": "not-json"}}]})))
    degraded = asyncio.run(LLMProvider().refine("technical", deterministic))
    assert degraded.runtime_mode == "degraded" and degraded.fallback_reason
    get_settings.cache_clear()
