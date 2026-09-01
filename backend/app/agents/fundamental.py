"""Fundamental agent constrained to retrieved filing passages."""
from datetime import date
from time import perf_counter

from app.schemas import AgentOutput, AgentStatus, Classification, Source
from app.services.retrieval import FilingRetriever, RetrievedChunk

QUERIES = {
    "revenue": "revenue growth trend demand",
    "profitability": "profitability operating margin trend costs",
    "debt": "debt leverage liquidity balance sheet",
    "guidance": "management guidance outlook expectations",
    "risks": "material risk delays volatility competition regulation",
}


async def run(symbol: str, retriever: FilingRetriever | None = None) -> AgentOutput:
    started = perf_counter()
    index = retriever or FilingRetriever()
    retrieved: list[RetrievedChunk] = []
    for query in QUERIES.values():
        retrieved.extend(index.retrieve(symbol, query, limit=1))
    unique = {chunk.chunk_id: chunk for chunk in retrieved}
    chunks = list(unique.values())
    if not chunks:
        return AgentOutput(agent="fundamental", status=AgentStatus.unavailable,
                           classification=Classification.insufficient_data, confidence=0,
                           summary="No filing passages were retrieved; no fundamental claims were generated.",
                           evidence=[], risks=[], sources=[], latency_ms=round((perf_counter() - started) * 1000, 3),
                           warnings=["Missing filing evidence"])
    corpus = " ".join(chunk.text.lower() for chunk in chunks)
    positives = sum(term in corpus for term in ("increased", "improved", "adequate", "low leverage", "resilient", "steady"))
    negatives = sum(term in corpus for term in ("moderated", "pressure", "delayed", "cautious", "volatility", "risk"))
    classification = Classification.strong if positives >= negatives + 2 else Classification.weak if negatives >= positives + 3 else Classification.mixed
    sources = [Source(title=f"Retrieved {symbol} filing passage", document=chunk.document,
                      date=date(2026, 9, 1), chunk_id=chunk.chunk_id) for chunk in chunks]
    evidence = [f"{chunk.chunk_id}: {chunk.text}" for chunk in chunks]
    risks = [chunk.text for chunk in chunks if "risk" in chunk.text.lower()]
    return AgentOutput(agent="fundamental", status=AgentStatus.completed, classification=classification,
                       confidence=min(86, 50 + len(chunks) * 6),
                       summary=f"Retrieved filing evidence is {classification.value}; every claim below maps to a filing chunk.",
                       evidence=evidence, risks=risks, sources=sources,
                       latency_ms=round((perf_counter() - started) * 1000, 3), warnings=["Filing document is simulated"])
