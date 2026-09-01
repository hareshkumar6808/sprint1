"""Sentiment classification over local synthetic news."""
import json
from pathlib import Path
from time import perf_counter

from app.schemas import AgentOutput, AgentStatus, Classification, Source

NEWS_FILE = Path(__file__).parent.parent / "data" / "news.json"


async def run(symbol: str, news_file: Path = NEWS_FILE) -> AgentOutput:
    started = perf_counter()
    records = [item for item in json.loads(news_file.read_text()) if item.get("symbol") == symbol]
    if not records:
        return AgentOutput(agent="sentiment", status=AgentStatus.unavailable,
                           classification=Classification.insufficient_data, confidence=0,
                           summary="No local news records are available; sentiment was not inferred.", evidence=[], risks=[], sources=[],
                           latency_ms=round((perf_counter() - started) * 1000, 3), warnings=["Missing sentiment input"])
    values = {"positive": 1, "neutral": 0, "mixed": 0, "negative": -1}
    score = sum(values.get(str(item.get("sentiment_hint")), 0) for item in records)
    classification = Classification.positive if score > 0 else Classification.negative if score < 0 else Classification.neutral
    sources = [Source(title=item["title"], document=item["url"], date=item["publication_date"], chunk_id=None)
               for item in records]
    evidence = [f"{item['title']}: {item['summary']} (hint: {item['sentiment_hint']})" for item in records]
    confidence = min(85, 45 + abs(score) * 12 + len(records) * 4)
    return AgentOutput(agent="sentiment", status=AgentStatus.completed, classification=classification,
                       confidence=confidence, summary=f"Local simulated news sentiment is {classification.value} across {len(records)} records.",
                       evidence=evidence, risks=["Synthetic sentiment hints are not independent market reporting"], sources=sources,
                       latency_ms=round((perf_counter() - started) * 1000, 3), warnings=["News records are simulated"])
