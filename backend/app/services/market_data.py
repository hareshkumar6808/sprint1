"""Provider interface boundary for simulated and optional live market data."""
from typing import Protocol

from app.schemas import MarketSnapshot


class MarketDataProvider(Protocol):
    def list_snapshots(self) -> list[MarketSnapshot]: ...

