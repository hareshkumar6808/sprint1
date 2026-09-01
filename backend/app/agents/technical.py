"""Deterministic technical signal agent."""
from time import perf_counter

from app.schemas import AgentOutput, AgentStatus, Classification, MarketSnapshot, Source
from app.services.market_data import calculate_features


async def run(snapshot: MarketSnapshot) -> AgentOutput:
    started = perf_counter()
    features = calculate_features(snapshot)
    score = 0
    score += 1 if snapshot.five_day_return is not None and snapshot.five_day_return > 1 else -1 if snapshot.five_day_return is not None and snapshot.five_day_return < -1 else 0
    score += 1 if snapshot.twenty_day_return is not None and snapshot.twenty_day_return > 2 else -1 if snapshot.twenty_day_return is not None and snapshot.twenty_day_return < -2 else 0
    score += 1 if features.moving_average_position_percent is not None and features.moving_average_position_percent > 1 else -1 if features.moving_average_position_percent is not None and features.moving_average_position_percent < -1 else 0
    score += 1 if features.volume_ratio is not None and features.volume_ratio >= 1.4 and score > 0 else -1 if features.volume_ratio is not None and features.volume_ratio >= 1.4 and score < 0 else 0
    available = sum(value is not None for value in (snapshot.five_day_return, snapshot.twenty_day_return,
                    features.moving_average_position_percent, features.volume_ratio, snapshot.rsi))
    classification = Classification.bullish if score >= 2 else Classification.bearish if score <= -2 else Classification.neutral
    risk_penalty = (8 if snapshot.volatility > 20 else 0) + (8 if snapshot.drawdown < -8 else 0)
    confidence = max(20, min(90, 55 + abs(score) * 9 - risk_penalty - (5-available)*8))
    risks = []
    if snapshot.volatility > 20:
        risks.append(f"Volatility is elevated at {snapshot.volatility:.1f}%")
    if snapshot.drawdown < -7:
        risks.append(f"Drawdown remains material at {snapshot.drawdown:.1f}%")
    return AgentOutput(
        agent="technical", status=AgentStatus.completed, classification=classification, confidence=confidence,
        summary=f"Technical indicators are {classification.value} based on deterministic momentum and risk thresholds.",
        evidence=[item for item in [f"5-day return: {snapshot.five_day_return:.1f}%" if snapshot.five_day_return is not None else None,
                  f"20-day return: {snapshot.twenty_day_return:.1f}%" if snapshot.twenty_day_return is not None else None,
                  f"Price versus 20-day average: {features.moving_average_position_percent:+.2f}%" if features.moving_average_position_percent is not None else None,
                  f"Volume ratio: {features.volume_ratio:.2f}x" if features.volume_ratio is not None else None,
                  f"RSI(14): {snapshot.rsi:.2f}" if snapshot.rsi is not None else None] if item],
        risks=risks,
        sources=[Source(title=f"{snapshot.symbol} {'simulated' if snapshot.simulated_data else snapshot.provider_name} market snapshot",
                        document="market_data.json" if snapshot.simulated_data else f"provider:{snapshot.provider_name}",
                        date=snapshot.data_timestamp.date(), chunk_id=None)],
        latency_ms=round((perf_counter() - started) * 1000, 3),
        warnings=(["Market data is simulated"] if snapshot.simulated_data else []) + snapshot.indicator_warnings,
    )
