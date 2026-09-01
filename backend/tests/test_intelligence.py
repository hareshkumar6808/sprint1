import asyncio
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import pytest
from fastapi.testclient import TestClient

from app.agents import behavioral, fundamental, sentiment, technical
from app.config import get_settings
from app.main import app
from app.schemas import AgentOutput, AgentStatus, Classification, MarketSnapshot, Profile
from app.services import orchestrator
from app.services.market_data import SimulatedMarketDataProvider, SymbolNotFoundError, calculate_features
from app.services.metrics import data_completeness, historical_accuracy, portfolio_concentration
from app.services.retrieval import FilingRetriever
from app.services.synthesizer import synthesize


def profile(risk: str = "moderate", maximum_volatility: float = 25, user_id: str = "unit-user") -> Profile:
    now = datetime.now(timezone.utc)
    return Profile(id=1, user_id=user_id, risk_profile=risk, investment_horizon_years=8,
                   maximum_volatility=maximum_volatility,
                   portfolio=[{"symbol": "TCS", "weight": 70}, {"symbol": "RELIANCE", "weight": 30}],
                   watchlist=["TCS"], interaction_history=[{"action": "viewed", "symbol": "TCS"}],
                   created_at=now, updated_at=now)


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def create_profile(client: TestClient, user_id: str, risk: str, max_volatility: float) -> None:
    response = client.post("/api/v1/profiles", json={
        "user_id": user_id, "risk_profile": risk, "investment_horizon_years": 8,
        "maximum_volatility": max_volatility,
        "portfolio": [{"symbol": "TCS", "weight": 70}, {"symbol": "RELIANCE", "weight": 30}],
        "watchlist": ["TCS"], "interaction_history": [{"action": "viewed", "symbol": "TCS"}],
    })
    assert response.status_code == 201


def test_market_service_calculates_features_and_rejects_unknown_symbol() -> None:
    provider = SimulatedMarketDataProvider()
    features = calculate_features(provider.get_snapshot("reliance"))
    assert features.volume_ratio == 1.51
    assert features.moving_average_position_percent > 0
    with pytest.raises(SymbolNotFoundError):
        provider.get_snapshot("FAKE")


def test_all_four_agents_and_degraded_sentiment() -> None:
    provider = SimulatedMarketDataProvider()
    reliance = provider.get_snapshot("RELIANCE")
    async def collect() -> list[AgentOutput]:
        return list(await asyncio.gather(
            technical.run(reliance), sentiment.run("RELIANCE"), fundamental.run("RELIANCE"),
            behavioral.run(profile(), reliance),
        ))

    outputs = asyncio.run(collect())
    assert [output.agent for output in outputs] == ["technical", "sentiment", "fundamental", "behavioral"]
    assert all(output.sources for output in outputs)
    missing = asyncio.run(sentiment.run("INFY"))
    assert missing.status == AgentStatus.unavailable
    assert missing.classification == Classification.insufficient_data
    assert not missing.evidence


def test_filing_retrieval_returns_traceable_chunks() -> None:
    retriever = FilingRetriever()
    chunks = retriever.retrieve("TCS", "revenue growth and delayed contracts", limit=2)
    assert chunks
    assert all(chunk.document == "TCS_Q1.txt" and chunk.chunk_id.startswith("TCS_Q1-chunk-") for chunk in chunks)
    output = asyncio.run(fundamental.run("TCS", retriever))
    assert output.sources
    assert all(source.chunk_id and source.document == "TCS_Q1.txt" for source in output.sources)
    assert all(any(source.chunk_id in evidence for evidence in output.evidence) for source in output.sources)


def test_orchestrator_runs_in_parallel_and_isolates_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    original = technical.run

    async def delayed(snapshot: MarketSnapshot) -> AgentOutput:
        await asyncio.sleep(0.04)
        return await original(snapshot)

    monkeypatch.setattr(technical, "run", delayed)
    snapshot = SimulatedMarketDataProvider().get_snapshot("RELIANCE")
    started = perf_counter()
    outputs, _ = asyncio.run(orchestrator.run_agents(snapshot, profile()))
    assert perf_counter() - started < 0.25
    assert len(outputs) == 4

    async def broken(_: MarketSnapshot) -> AgentOutput:
        raise RuntimeError("isolated test failure")

    monkeypatch.setattr(technical, "run", broken)
    outputs, _ = asyncio.run(orchestrator.run_agents(snapshot, profile()))
    assert outputs[0].status == AgentStatus.failed
    assert all(output.status != AgentStatus.failed for output in outputs[1:])


def test_positive_conflicting_and_degraded_api_scenarios(client: TestClient) -> None:
    create_profile(client, "scenario-user", "moderate", 25)
    reliance = client.post("/api/v1/analyze", json={"user_id": "scenario-user", "symbol": "RELIANCE"})
    tcs = client.post("/api/v1/analyze", json={"user_id": "scenario-user", "symbol": "TCS"})
    infy = client.post("/api/v1/analyze", json={"user_id": "scenario-user", "symbol": "INFY"})
    assert reliance.status_code == tcs.status_code == infy.status_code == 200
    assert reliance.json()["market_signal"] == "bullish"
    assert reliance.json()["synthesis"]["confidence"] > infy.json()["synthesis"]["confidence"]
    assert tcs.json()["synthesis"]["conflicts"]
    assert infy.json()["metrics"]["data_completeness_percent"] == 75
    sentiment_output = next(item for item in infy.json()["agents"] if item["agent"] == "sentiment")
    assert sentiment_output["status"] == "unavailable"


def test_invalid_symbol_missing_profile_and_log_persistence(client: TestClient) -> None:
    assert client.post("/api/v1/analyze", json={"user_id": "missing", "symbol": "TCS"}).status_code == 404
    create_profile(client, "logged-user", "moderate", 25)
    assert client.post("/api/v1/analyze", json={"user_id": "logged-user", "symbol": "FAKE"}).status_code == 404
    analyzed = client.post("/api/v1/analyze", json={"user_id": "logged-user", "symbol": "RELIANCE"})
    logs = client.get("/api/v1/logs/logged-user")
    assert logs.status_code == 200
    assert logs.json()[0]["analysis_id"] == analyzed.json()["analysis_id"]
    assert logs.json()[0]["agents"] == analyzed.json()["agents"]


def test_conservative_and_aggressive_personalization_differs(client: TestClient) -> None:
    create_profile(client, "conservative-user", "conservative", 15)
    create_profile(client, "aggressive-user", "aggressive", 35)
    conservative = client.post("/api/v1/analyze", json={"user_id": "conservative-user", "symbol": "TCS"}).json()
    aggressive = client.post("/api/v1/analyze", json={"user_id": "aggressive-user", "symbol": "TCS"}).json()
    conservative_behavior = next(item for item in conservative["agents"] if item["agent"] == "behavioral")
    aggressive_behavior = next(item for item in aggressive["agents"] if item["agent"] == "behavioral")
    assert conservative_behavior["classification"] == "unsuitable"
    assert aggressive_behavior["classification"] == "suitable"
    assert conservative["synthesis"]["personalized_guidance"] != aggressive["synthesis"]["personalized_guidance"]


def test_no_uncited_recommendation_and_confidence_reduction() -> None:
    failed = [AgentOutput(agent=name, status=AgentStatus.unavailable,
                          classification=Classification.insufficient_data, confidence=0,
                          summary="missing", evidence=[], risks=[], sources=[], latency_ms=1, warnings=["missing"])
              for name in ("technical", "sentiment", "fundamental", "behavioral")]
    signal, result, _ = synthesize(failed)
    assert signal == Classification.insufficient_data
    assert result.confidence == 0 and not result.evidence_used
    assert "investigate further" in result.personalized_guidance.lower()

    snapshot = SimulatedMarketDataProvider().get_snapshot("RELIANCE")
    completed = asyncio.run(technical.run(snapshot))
    _, complete_result, _ = synthesize([completed])
    _, degraded_result, _ = synthesize([completed, *failed[:1]])
    assert degraded_result.confidence < complete_result.confidence


def test_metrics_calculations() -> None:
    assert historical_accuracy("TCS") == 50
    assert portfolio_concentration(profile()) == 64
    completed = AgentOutput(agent="technical", status=AgentStatus.completed, classification=Classification.neutral,
                            confidence=50, summary="x", latency_ms=1)
    unavailable = completed.model_copy(update={"agent": "sentiment", "status": AgentStatus.unavailable})
    assert data_completeness([completed, unavailable]) == 50
