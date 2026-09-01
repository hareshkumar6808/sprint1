from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import initialize_database
from app.routes import analysis, health, logs, profiles, stocks


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
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
for route in (stocks.router, profiles.router, analysis.router, logs.router):
    app.include_router(route, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"project": "FinSync Intelligence", "service": "finsync-intelligence-api", "version": settings.version}
