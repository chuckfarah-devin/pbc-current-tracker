"""
Nearshore current service — fetch chain (best resolution wins):

  1. NWPS ERDDAP   ~750 m   NOAA Nearshore Wave Prediction System
  2. HYCOM GLBy0.08  ~8 km   Global ocean model via THREDDS
  3. Windy API       ~9 km   Copernicus/HYCOM (requires free API key)
  4. NOAA CO-OPS    Point   Tidal proxy fallback (from noaa_currents.py)

All keys/credentials are optional — any step that fails is silently skipped.
Set WINDY_API_KEY in .env to enable Windy.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings
from app.models.conditions import CurrentData
from app.services.noaa_currents import fetch_noaa_currents   # tidal fallback

logger = logging.getLogger(__name__)

# ── NWPS (NOAA Nearshore Wave Prediction System) via ERDDAP griddap ──────────
# Dataset: nwpsWW3_5m — 5-minute (~750 m) resolution current components
_NWPS_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
_NWPS_DATASET = "nwpsWW3_5m"   # adjust if ERDDAP dataset ID changes

# ── HYCOM GLBy0.08 via THREDDS OPeNDAP ───────────────────────────────────────
# We use the HYCOM Data Server JSON endpoint (simpler than full OPeNDAP):
_HYCOM_BASE = "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0/uv3z"
# Simpler REST alternative that HYCOM sometimes exposes:
_HYCOM_REST = "https://tds.hycom.org/thredds/dodsC/GLBy0.08/latest.ascii"

# ── Windy Point Forecast API ──────────────────────────────────────────────────
_WINDY_URL = "https://api.windy.com/api/point-forecast/v2"

_RESOLUTION_NWPS = 750
_RESOLUTION_HYCOM = 8000
_RESOLUTION_WINDY = 9000

def _uv_to_speed_dir(u: float, v: float) -> tuple[float, float]:
    """Convert u (east) / v (north) current components to speed and oceanographic direction."""
    speed = math.sqrt(u ** 2 + v ** 2)
    # Oceanographic convention: direction water is moving TOWARDS
    direction = (270 - math.degrees(math.atan2(v, u))) % 360
    return round(speed, 3), round(direction, 1)


async def _fetch_nwps(client: httpx.AsyncClient, lat: float, lon: float) -> Optional[CurrentData]:
    """
    Try NOAA NWPS ERDDAP for nearshore current (u, v) components.
    Returns CurrentData with resolution_m=750 on success, None on any failure.
    """
    # ERDDAP griddap CSV: fetch single point nearest to lat/lon, last time step
    # u_current and v_current variables (check actual var names on the dataset)
    url = (
        f"{_NWPS_BASE}/{_NWPS_DATASET}.csv"
        f"?u_current[(last)][(0.0):1:(0.0)][({lat}):1:({lat})][({lon}):1:({lon})]"
        f",v_current[(last)][(0.0):1:(0.0)][({lat}):1:({lat})][({lon}):1:({lon})]"
    )
    try:
        resp = await client.get(url, timeout=20.0)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        if len(lines) < 3:
            return None
        # Row format: time, altitude, latitude, longitude, u_current, v_current
        parts = lines[2].split(",")
        if len(parts) < 6:
            return None
        u = float(parts[4].strip())
        v = float(parts[5].strip())
        ts_str = parts[0].strip()
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(tz=timezone.utc)
        speed, direction = _uv_to_speed_dir(u, v)
        logger.info("NWPS current: %.2f m/s @ %.0f deg (750 m res)", speed, direction)
        return CurrentData(
            speed_mps=speed,
            direction_deg=direction,
            source="NWPS",
            resolution_m=_RESOLUTION_NWPS,
            timestamp=ts,
        )
    except Exception as exc:
        logger.debug("NWPS fetch failed: %s", exc)
        return None

async def _fetch_hycom(client: httpx.AsyncClient, lat: float, lon: float) -> Optional[CurrentData]:
    """
    Fetch surface current from HYCOM GLBy0.08 via the HYCOM data server REST API.
    HYCOM provides a simpler ASCII/JSON subset endpoint we can parse.
    Falls back to None on any error.
    """
    # HYCOM data server: https://tds.hycom.org/thredds/dodsC/
    # The simplest accessible form is the HYCOM OPeNDAP ASCII endpoint.
    # We request the surface (depth index 0) u and v at the nearest grid point.
    # Note: HYCOM grid is 0.08 deg (~8 km). Lon in HYCOM is 0-360.
    hycom_lon = lon + 360 if lon < 0 else lon
    url = (
        "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0/uv3z.ascii"
        f"?water_u[0][0][0:1:0][0:1:0]"  # placeholder; real query needs index lookup
        # Full OPeNDAP lat/lon index resolution is complex; use HYCOM REST instead
    )
    # Simpler: use the HYCOM NCSS (NetCDF Subset Service) which accepts lat/lon directly
    ncss_url = "https://tds.hycom.org/thredds/ncss/GLBy0.08/expt_93.0/uv3z"
    params = {
        "var": ["water_u", "water_v"],
        "latitude": lat,
        "longitude": hycom_lon,
        "vertCoord": 0,
        "time": "present",
        "accept": "csv",
    }
    try:
        resp = await client.get(ncss_url, params=params, timeout=20.0)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        # HYCOM NCSS CSV: date, lat, lon, depth, water_u, water_v
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                u = float(parts[4])
                v = float(parts[5])
                speed, direction = _uv_to_speed_dir(u, v)
                logger.info("HYCOM current: %.2f m/s @ %.0f deg (~8 km res)", speed, direction)
                return CurrentData(
                    speed_mps=speed,
                    direction_deg=direction,
                    source="HYCOM",
                    resolution_m=_RESOLUTION_HYCOM,
                    timestamp=datetime.now(tz=timezone.utc),
                )
    except Exception as exc:
        logger.debug("HYCOM fetch failed: %s", exc)
    return None

async def _fetch_windy(client: httpx.AsyncClient, lat: float, lon: float) -> Optional[CurrentData]:
    """
    Fetch surface current from Windy Point Forecast API (Copernicus CMEMS model).
    Requires WINDY_API_KEY set in environment.  ~9 km resolution.
    Free tier: https://api.windy.com/api/point-forecast/v2
    """
    api_key = getattr(settings, "windy_api_key", None)
    if not api_key:
        logger.debug("Windy API key not configured; skipping")
        return None

    payload = {
        "lat": lat,
        "lon": lon,
        "model": "gfs",
        "parameters": ["waves"],
        "key": api_key,
    }
    # Windy current data comes from the "currents" model
    current_payload = {
        "lat": lat,
        "lon": lon,
        "model": "gfsWave",
        "parameters": ["currents"],
        "key": api_key,
    }
    try:
        resp = await client.post(_WINDY_URL, json=current_payload, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        # Windy response: {"currentUs-surface": [...], "currentVs-surface": [...]}
        us = data.get("currentUs-surface", [])
        vs = data.get("currentVs-surface", [])
        if us and vs:
            u = float(us[0])
            v = float(vs[0])
            speed, direction = _uv_to_speed_dir(u, v)
            logger.info("Windy current: %.2f m/s @ %.0f deg (~9 km res)", speed, direction)
            return CurrentData(
                speed_mps=speed,
                direction_deg=direction,
                source="Windy",
                resolution_m=_RESOLUTION_WINDY,
                timestamp=datetime.now(tz=timezone.utc),
            )
    except Exception as exc:
        logger.debug("Windy fetch failed: %s", exc)
    return None


async def fetch_best_current(client: httpx.AsyncClient, lat: float, lon: float) -> CurrentData:
    """
    Try data sources in order of resolution. Return the first that succeeds.
    Falls back all the way to the NOAA CO-OPS tidal proxy.
    """
    # 1. NWPS (~750 m) — best for nearshore
    result = await _fetch_nwps(client, lat, lon)
    if result is not None:
        return result

    # 2. HYCOM (~8 km)
    result = await _fetch_hycom(client, lat, lon)
    if result is not None:
        return result

    # 3. Windy (~9 km, requires key)
    result = await _fetch_windy(client, lat, lon)
    if result is not None:
        return result

    # 4. NOAA CO-OPS tidal proxy (no resolution_m — point observation)
    logger.warning("All nearshore current sources failed; using tidal proxy")
    result = await fetch_noaa_currents(client)
    return result
