"""GET /api/conditions -- orchestrates all data sources (v0.2)."""
import asyncio
import logging

import httpx
from fastapi import APIRouter, Query

from app.config import settings
from app.models.conditions import ConditionsResponse, LocationInfo
from app.services import cache as cache_svc
from app.services.hycom_currents import fetch_best_current
from app.services.plume import classify_plume, compute_snorkel_index, enrich_plume_with_current
from app.services.sentinel_turbidity import fetch_best_turbidity
from app.services.sfwmd import fetch_c16_runoff
from app.services.usace import fetch_lake_o_data

logger = logging.getLogger(__name__)
router = APIRouter()


def _nearshore_quality(current_res: int | None, clarity: int | None) -> str:
    """Derive a simple nearshore quality label from resolution + clarity."""
    c = clarity if clarity is not None else 0
    r = current_res if current_res is not None else 99999
    if r <= 100 and c >= 60:
        return "excellent"
    if r <= 1000 and c >= 40:
        return "good"
    if r <= 9000 and c >= 20:
        return "fair"
    return "poor"


@router.get("/conditions", response_model=ConditionsResponse)
async def get_conditions(
    lat: float = Query(default=settings.inlet_lat, description="Latitude"),
    lon: float = Query(default=settings.inlet_lon, description="Longitude"),
) -> ConditionsResponse:
    cache_key = f"conditions_{lat:.2f}_{lon:.2f}"
    cached = cache_svc.get(cache_key)
    if cached is not None:
        logger.debug("Cache hit for %s", cache_key)
        return cached

    async with httpx.AsyncClient(
        headers={"User-Agent": "PBC-Plume-Tracker/1.0"},
        follow_redirects=True,
    ) as client:
        current, turbidity, runoff, lake_o = await asyncio.gather(
            fetch_best_current(client, lat, lon),
            fetch_best_turbidity(client, lat, lon),
            fetch_c16_runoff(client),
            fetch_lake_o_data(client),
        )

    plume = classify_plume(runoff, lake_o, current_resolution_m=current.resolution_m)
    plume = enrich_plume_with_current(plume, current)
    snorkel_index = compute_snorkel_index(turbidity, current, runoff, lake_o, plume)
    nq = _nearshore_quality(current.resolution_m, turbidity.clarity_score)

    response = ConditionsResponse(
        location=LocationInfo(lat=lat, lon=lon),
        current=current,
        turbidity=turbidity,
        runoff=runoff,
        lake_o=lake_o,
        plume=plume,
        snorkel_index=snorkel_index,
        nearshore_quality=nq,
    )
    cache_svc.set_with_ts(cache_key, response)
    return response
