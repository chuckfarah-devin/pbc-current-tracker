"""GET /api/status — system health and last-update timestamps."""
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.conditions import SourceStatus, StatusResponse
from app.services import cache as cache_svc

router = APIRouter()
_DEFAULT_CACHE_KEY = "conditions_26.53_-80.05"


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    now = datetime.now(tz=timezone.utc)
    source_names = ["noaa_currents", "sat_turbidity", "sfwmd_c16", "usace_lake_o"]
    sources: dict[str, SourceStatus] = {}
    overall_ok = True

    ts_unix = cache_svc.get_ts(_DEFAULT_CACHE_KEY)
    for name in source_names:
        if ts_unix is None:
            sources[name] = SourceStatus(status="unknown")
            overall_ok = False
        else:
            age = time.time() - ts_unix
            dt = datetime.fromtimestamp(ts_unix, tz=timezone.utc)
            status = "stale" if age > 7200 else "ok"
            if status != "ok":
                overall_ok = False
            sources[name] = SourceStatus(last_update=dt, status=status)

    return StatusResponse(
        status="ok" if overall_ok else "degraded",
        last_update=now,
        sources=sources,
    )
