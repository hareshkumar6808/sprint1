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
          sources_json TEXT NOT NULL, warnings_json TEXT NOT NULL, response_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_decisions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, ticker TEXT NOT NULL,
          action TEXT NOT NULL, analysis_id TEXT NOT NULL, current_signal TEXT NOT NULL,
          confidence INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS instruments (
          instrument_key TEXT PRIMARY KEY, exchange TEXT NOT NULL, segment TEXT NOT NULL,
          symbol TEXT NOT NULL, name TEXT NOT NULL, isin TEXT, tick_size REAL, lot_size INTEGER,
          instrument_type TEXT NOT NULL, last_synced_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_instruments_name ON instruments(name COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_instruments_exchange ON instruments(exchange);
        CREATE TABLE IF NOT EXISTS catalogue_sync (
          provider TEXT PRIMARY KEY, status TEXT NOT NULL, last_attempt_at TEXT,
          last_success_at TEXT, instrument_count INTEGER NOT NULL DEFAULT 0, error TEXT
        );
        CREATE TABLE IF NOT EXISTS instrument_documents (
          id INTEGER PRIMARY KEY AUTOINCREMENT, instrument_key TEXT NOT NULL, symbol TEXT NOT NULL,
          company_name TEXT NOT NULL, title TEXT NOT NULL, document_type TEXT NOT NULL,
          source_date TEXT NOT NULL, attribution TEXT NOT NULL, local_path TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS profile_holdings (
          user_id TEXT NOT NULL, instrument_key TEXT NOT NULL, symbol TEXT NOT NULL,
          exchange TEXT, allocation REAL, quantity REAL, value REAL,
          PRIMARY KEY(user_id,instrument_key)
        );
        CREATE TABLE IF NOT EXISTS profile_watchlist (
          user_id TEXT NOT NULL, instrument_key TEXT NOT NULL,
          PRIMARY KEY(user_id,instrument_key)
        );
        """)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_logs)")}
        if "response_json" not in columns:
            try:
                conn.execute("ALTER TABLE analysis_logs ADD COLUMN response_json TEXT")
            except sqlite3.OperationalError as exc:
                if "duplicate column" not in str(exc).lower():
                    raise


def encode_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"))
