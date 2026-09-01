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
          expanded_profile_json TEXT NOT NULL DEFAULT '{}',
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
          instrument_type TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'unknown', last_synced_at TEXT NOT NULL
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
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, event_key TEXT UNIQUE NOT NULL, instrument_key TEXT,
          symbol TEXT NOT NULL, event_type TEXT NOT NULL, severity TEXT NOT NULL,
          evidence_json TEXT NOT NULL, occurred_at TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS journals (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, symbol TEXT NOT NULL,
          thesis TEXT NOT NULL, action TEXT NOT NULL, holding_period TEXT, catalyst TEXT,
          reconsideration_condition TEXT, confidence INTEGER NOT NULL, notes TEXT,
          outcome TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS predictions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_id TEXT UNIQUE NOT NULL, instrument_key TEXT,
          symbol TEXT NOT NULL, prediction_timestamp TEXT NOT NULL, price REAL NOT NULL,
          direction TEXT NOT NULL, raw_confidence INTEGER NOT NULL, calibrated_confidence INTEGER,
          horizon_days INTEGER NOT NULL, evidence_snapshot_json TEXT NOT NULL, version TEXT NOT NULL,
          forward_return REAL, direction_correct INTEGER, evaluated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, investigation_id TEXT, event_type TEXT NOT NULL,
          status TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_logs)")}
        if "response_json" not in columns:
            try:
                conn.execute("ALTER TABLE analysis_logs ADD COLUMN response_json TEXT")
            except sqlite3.OperationalError as exc:
                if "duplicate column" not in str(exc).lower():
                    raise
        instrument_columns = {row["name"] for row in conn.execute("PRAGMA table_info(instruments)")}
        if "category" not in instrument_columns:
            conn.execute("ALTER TABLE instruments ADD COLUMN category TEXT NOT NULL DEFAULT 'unknown'")
        # Some Upstox master records omit the separate ISIN field while retaining it
        # as the stable identity after `|` in instrument_key. Recover it so category
        # filters do not hide valid stocks/ETFs already cached in older databases.
        conn.execute("""UPDATE instruments SET isin=substr(instrument_key,instr(instrument_key,'|')+1)
          WHERE (isin IS NULL OR isin='') AND instr(instrument_key,'|')>0 AND
          (upper(substr(instrument_key,instr(instrument_key,'|')+1)) LIKE 'INE%' OR
           upper(substr(instrument_key,instr(instrument_key,'|')+1)) LIKE 'INF%')""")
        conn.execute("UPDATE instruments SET category='stock' WHERE upper(isin) LIKE 'INE%' AND category!='stock'")
        conn.execute("UPDATE instruments SET category='etf_fund' WHERE upper(isin) LIKE 'INF%' AND category!='etf_fund'")
        profile_columns = {row["name"] for row in conn.execute("PRAGMA table_info(user_profiles)")}
        if "expanded_profile_json" not in profile_columns:
            conn.execute("ALTER TABLE user_profiles ADD COLUMN expanded_profile_json TEXT NOT NULL DEFAULT '{}'")


def encode_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"))
