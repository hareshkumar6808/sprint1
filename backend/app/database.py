import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings


def database_path() -> Path:
    url = get_settings().database_url
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError("Only sqlite:/// database URLs are supported")
    return Path(url.removeprefix(prefix)).resolve()


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(database_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_database() -> None:
    with connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_profiles (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT UNIQUE NOT NULL,
          risk_profile TEXT NOT NULL, investment_horizon_years INTEGER NOT NULL,
          maximum_volatility REAL NOT NULL, portfolio_json TEXT NOT NULL,
          watchlist_json TEXT NOT NULL, interaction_history_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS analysis_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_id TEXT UNIQUE NOT NULL,
          user_id TEXT NOT NULL, symbol TEXT NOT NULL, market_classification TEXT NOT NULL,
          recommendation TEXT NOT NULL, confidence REAL NOT NULL, latency_ms REAL NOT NULL,
          historical_accuracy REAL NOT NULL, concentration_score REAL NOT NULL,
          data_completeness REAL NOT NULL, agent_outputs_json TEXT NOT NULL,
          sources_json TEXT NOT NULL, warnings_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)


def encode_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"))

