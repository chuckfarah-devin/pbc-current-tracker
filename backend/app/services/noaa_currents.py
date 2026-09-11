"""
NOAA CO-OPS current predictions + tidal-stage fallback.

Current station: ACT1816 (nearest prediction to Lake Worth Inlet)
Tidal fallback:  8722669 (Lake Worth Pier water-level gauge)
No API key required.
Docs: https://api.tidesandcurrents.noaa.gov/api/prod/
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.models.conditions import CurrentData

logger = logging.getLogger(__name__)
_COOPS = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
_CURR_STA = "ACT1816"
_TIDE_STA = "8723214"  # Virginia Key Miami (reliable real-time)


async def fetch_noaa_currents(client: httpx.AsyncClient) -> CurrentData:
    now = datetime.now(tz=timezone.utc)
    begin = (now - timedelta(hours=2)).strftime("%Y%m%d %H:%M")
    end   = now.strftime("%Y%m%d %H:%M")
    params = {
        "station": _CURR_STA, "product": "currents_predictions",
        "begin_date": begin, "end_date": end,
        "time_zone": "GMT", "interval": "h", "units": "metric",
        "application": "PBC-Plume-Tracker", "format": "json",
    }
    try:
        resp = await client.get(_COOPS, params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.warning("NOAA CO-OPS error: %s", data["error"])
            return await _tidal_fallback(client, now)
        preds = data.get("current_predictions", {}).get("cp", [])
        if not preds:
            return await _tidal_fallback(client, now)
        latest = preds[-1]
        speed = float(latest.get("Speed", 0))
        direction = float(latest.get("meanFloodDir", 0))
        try:
            ts = datetime.strptime(latest["Time"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            ts = now
        logger.info("NOAA currents: %.2f m/s @ %.0f deg", speed, direction)
        return CurrentData(speed_mps=round(speed, 3), direction_deg=round(direction, 1),
                           source="NOAA_COOPS", timestamp=ts)
    except Exception as exc:
        logger.error("NOAA fetch failed: %s", exc)
        return await _tidal_fallback(client, now)


async def _tidal_fallback(client: httpx.AsyncClient, now: datetime) -> CurrentData:
    """Infer flood/ebb from water-level trend at Lake Worth gauge."""
    begin = (now - timedelta(hours=3)).strftime("%Y%m%d %H:%M")
    end   = now.strftime("%Y%m%d %H:%M")
    params = {
        "station": _TIDE_STA, "product": "water_level", "datum": "MLLW",
        "begin_date": begin, "end_date": end,
        "time_zone": "GMT", "units": "metric",
        "application": "PBC-Plume-Tracker", "format": "json",
    }
    try:
        resp = await client.get(_COOPS, params=params, timeout=15.0)
        resp.raise_for_status()
        levels = resp.json().get("data", [])
        if len(levels) >= 2:
            trend = float(levels[-1]["v"]) - float(levels[-2]["v"])
            direction = 0.0 if trend >= 0 else 180.0
            logger.info("Tidal proxy: %s, direction=%.0f", "flood" if trend >= 0 else "ebb", direction)
            return CurrentData(speed_mps=0.15, direction_deg=direction,
                               source="NOAA_COOPS_tidal_proxy",
                               timestamp=datetime.now(tz=timezone.utc))
    except Exception as exc:
        logger.error("Tidal fallback failed: %s", exc)
    return CurrentData(error="NOAA current data unavailable")
