"""
USACE Lake Okeechobee structure flows via the Hydromet REST API.
East-coast structures: S-80 (primary), S-351, S-352, S-354
West-coast (reference): S-308
Lake stage: LZ40 (open-water centre gauge)
"""
import logging
from datetime import datetime, timezone
from typing import Optional
import httpx
from app.models.conditions import LakeOData, LakeOStructures

logger = logging.getLogger(__name__)
_BASE = "https://apps.saj.usace.army.mil/eim/api"
_SERIES = {
    "S308": "S308.HW.FLOW-MEAN.1Day.1Day.Best",
    "S80":  "S80.HW.FLOW-MEAN.1Day.1Day.Best",
    "S351": "S351.HW.FLOW-MEAN.1Day.1Day.Best",
    "S352": "S352.HW.FLOW-MEAN.1Day.1Day.Best",
    "S354": "S354.HW.FLOW-MEAN.1Day.1Day.Best",
}
_STAGE = "LZ40.HW.GAGE-HT.1Day.1Day.Best"
_EAST = ["S80", "S351", "S352", "S354"]


async def _latest(client: httpx.AsyncClient, sid: str) -> Optional[float]:
    try:
        resp = await client.get(f"{_BASE}/hydromet/latest/{sid}", timeout=15.0)
        resp.raise_for_status()
        val = resp.json().get("value")
        return float(val) if val is not None else None
    except Exception as exc:
        logger.debug("Hydromet %s: %s", sid, exc)
        return None


async def fetch_lake_o_data(client: httpx.AsyncClient) -> LakeOData:
    flows: dict[str, Optional[float]] = {}
    errors: list[str] = []

    for name, sid in _SERIES.items():
        val = await _latest(client, sid)
        flows[name] = val
        if val is None:
            errors.append(f"{name} unavailable")
        else:
            logger.info("USACE %s: %.0f cfs", name, val)

    lake_stage = await _latest(client, _STAGE)
    if lake_stage is not None:
        logger.info("Lake O stage: %.2f ft", lake_stage)

    east_vals = [flows[s] for s in _EAST if flows.get(s) is not None]
    east_total: Optional[float] = sum(east_vals) if east_vals else None

    influence = "unknown"
    if east_total is not None:
        influence = "high" if east_total >= 2000 else ("med" if east_total >= 500 else "low")

    return LakeOData(
        lake_stage_ft=lake_stage,
        east_discharge_cfs_total=east_total,
        structures=LakeOStructures(
            S308=flows.get("S308"), S80=flows.get("S80"),
            S351=flows.get("S351"), S352=flows.get("S352"), S354=flows.get("S354"),
        ),
        lake_o_influence=influence,
        timestamp=datetime.now(tz=timezone.utc),
        error=(" | ".join(errors) if errors else None),
    )
