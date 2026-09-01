"""Failure-isolated concurrent agent orchestration."""
import asyncio
from collections.abc import Awaitable
from datetime import datetime, timezone
from time import perf_counter
from typing import Literal

from app.agents import behavioral, fundamental, sentiment, technical
from app.schemas import AgentOutput, AgentStatus, Classification, MarketSnapshot, Profile
from app.services.retrieval import FilingRetriever
from app.services.llm_provider import LLMProvider

AgentName = Literal["technical", "sentiment", "fundamental", "behavioral"]


async def _safe(name: AgentName, operation: Awaitable[AgentOutput]) -> AgentOutput:
    started = perf_counter()
    started_at = datetime.now(timezone.utc)
    try:
        output = await operation
        return output.model_copy(update={"started_at": started_at, "ended_at": datetime.now(timezone.utc),
                                         "evidence_ids": output.evidence_ids or [source.source_id or source.chunk_id or source.document for source in output.sources]})
    except Exception as exc:  # individual failures must remain isolated
        return AgentOutput(agent=name, status=AgentStatus.failed, classification=Classification.insufficient_data,
                           confidence=0, summary=f"{name.title()} agent failed without stopping other agents.",
                           evidence=[], risks=[], sources=[], latency_ms=round((perf_counter() - started) * 1000, 3),
                           warnings=[f"{type(exc).__name__}: {exc}"], started_at=started_at,
                           ended_at=datetime.now(timezone.utc))


async def run_agents(snapshot: MarketSnapshot, profile: Profile,
                     retriever: FilingRetriever | None = None) -> tuple[list[AgentOutput], float]:
    started = perf_counter()
    deterministic = await asyncio.gather(
        _safe("technical", technical.run(snapshot)),
        _safe("sentiment", sentiment.run(snapshot.symbol)),
        _safe("fundamental", fundamental.run(snapshot.symbol, retriever, snapshot.company_name,
                                               snapshot.instrument_key.split("|", 1)[1] if snapshot.instrument_key and "|" in snapshot.instrument_key else None)),
        _safe("behavioral", behavioral.run(profile, snapshot)),
    )
    provider = LLMProvider()
    outputs = await asyncio.gather(*(provider.refine(output.agent, output) for output in deterministic))
    return list(outputs), round((perf_counter() - started) * 1000, 3)
