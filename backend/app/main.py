from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import initialize_database
from app.routes import analysis, decisions, documents, health, instruments, logs, market, profiles, stocks
from app.services.instruments import seed_fixture_if_empty
from app.services.instruments import sync_catalogue


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    seed_fixture_if_empty()
    if settings.market_data_mode == "live":
        sync_catalogue()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
local_frontend_origins = list(dict.fromkeys([
    settings.frontend_origin,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]))
app.add_middleware(CORSMiddleware, allow_origins=local_frontend_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router)
for route in (stocks.router, profiles.router, analysis.router, logs.router, decisions.router,
              instruments.router, market.router, documents.router):
    app.include_router(route, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"project": "FinSync Intelligence", "service": "finsync-intelligence-api", "version": settings.version}
