from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FinSync Intelligence API"
    version: str = "0.1.0"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    database_url: str = "sqlite:///./finsync_intelligence.db"
    market_data_mode: str = "simulated"
    market_data_provider: str = "upstox"
    market_data_api_key: str | None = None
    upstox_access_token: str | None = None
    upstox_instrument_master_url: str = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
    instrument_refresh_hours: int = 20
    quote_cache_seconds: int = 15
    candle_cache_seconds: int = 900
    market_request_timeout_seconds: float = 8.0
    llm_provider: str = "openai"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 12.0
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    semantic_retrieval_enabled: bool = True
    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
