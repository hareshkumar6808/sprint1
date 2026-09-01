"""Failure-isolated concurrent agent orchestration."""
import asyncio
from collections.abc import Awaitable
from time import perf_counter
from typing import Literal

from app.agents import behavioral, fundamental, sentiment, technical
from app.schemas import AgentOutput, AgentStatus, Classification, MarketSnapshot, Profile
from app.services.retrieval import FilingRetriever

AgentName = Literal["technical", "sentiment", "fundamental", "behavioral"]


async def _safe(name: AgentName, operation: Awaitable[AgentOutput]) -> AgentOutput:
    started = perf_counter()
    try:
        return await operation
    except Exception as exc:  # individual failures must remain isolated
        return AgentOutput(agent=name, status=AgentStatus.failed, classification=Classification.insufficient_data,
                           confidence=0, summary=f"{name.title()} agent failed without stopping other agents.",
                           evidence=[], risks=[], sources=[], latency_ms=round((perf_counter() - started) * 1000, 3),
                           warnings=[f"{type(exc).__name__}: {exc}"])


async def run_agents(snapshot: MarketSnapshot, profile: Profile,
                     retriever: FilingRetriever | None = None) -> tuple[list[AgentOutput], float]:
    started = perf_counter()
    outputs = await asyncio.gather(
        _safe("technical", technical.run(snapshot)),
        _safe("sentiment", sentiment.run(snapshot.symbol)),
        _safe("fundamental", fundamental.run(snapshot.symbol, retriever)),
        _safe("behavioral", behavioral.run(profile, snapshot)),
    )
    return list(outputs), round((perf_counter() - started) * 1000, 3)
