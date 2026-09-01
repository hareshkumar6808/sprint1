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
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router)
for route in (stocks.router, profiles.router, analysis.router, logs.router):
    app.include_router(route, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"project": "FinSync Intelligence", "service": "finsync-intelligence-api", "version": settings.version}

