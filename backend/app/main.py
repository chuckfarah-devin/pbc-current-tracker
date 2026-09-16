"""
Palm Beach Plume Tracker — FastAPI backend.

Run locally:
    cd backend
    uvicorn app.main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import conditions as conditions_router
from app.routers import snorkel_conditions as snorkel_router
from app.routers import status as status_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _log.info("PBC Plume Tracker starting — inlet %.4f, %.4f", settings.inlet_lat, settings.inlet_lon)
    yield
    _log.info("Shutting down")


app = FastAPI(
    title="Palm Beach Plume Tracker",
    description="Real-time nearshore water-quality API for snorkelers around Boynton Inlet.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(status_router.router, prefix="/api", tags=["status"])
app.include_router(conditions_router.router, prefix="/api", tags=["conditions"])
app.include_router(snorkel_router.router, prefix="/api", tags=["snorkel"])

# Serve recorded PoC demo assets (camera, appearance, sargassum, motion images)
# for the replay endpoint. This is mounted only when the handoff directory exists.
_replay_assets = Path(settings.poc_handoff_dir) / settings.replay_demo_dir
if _replay_assets.is_dir():
    app.mount("/fixtures", StaticFiles(directory=_replay_assets), name="fixtures")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": "Palm Beach Plume Tracker API", "docs": "/docs"}
