"""
SFWMD DBHYDRO client — C-16 discharge (S-41) and 24h rainfall.

DBHYDRO is SFWMD's public hydro database, no API key required.
REST endpoint: https://my.sfwmd.gov/dbhydroplsql/web_io.report_process

Stations used:
  S41  – S-41 gate structure (C-16 canal to Intracoastal)
  1C7  – Rain gauge near Boynton Beach / C-16 basin
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.models.conditions import RunoffData

logger = logging.getLogger(__name__)

_DBHYDRO_BASE = "https://my.sfwmd.gov/dbhydroplsql/web_io.report_process"
_BASE_PARAMS = {
    "v_js_flag": "Y",
    "v_period": "uspec",
    "v_group_by": "STATION",
    "v_calib_flag": "Y",
    "v_run_mode": "C",
    "v_separator": ",",
}
_RAIN_STATION = "1C7"


def _date_window(days_back: int = 2) -> tuple[str, str]:
    now = datetime.now(tz=timezone.utc)
    start = now - timedelta(days=days_back)
    return start.strftime("%m/%d/%Y"), now.strftime("%m/%d/%Y")


def _parse_dbhydro_csv(text: str) -> list[tuple[datetime, float]]:
    rows = []
    in_data = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "STATION" in line and "DATE" in line:
            in_data = True
            continue
        if not in_data:
            continue
        parts = line.split(",")
        if len(parts) < 5:
            continue
        try:
            dt = datetime.strptime(
                f"{parts[2].strip()} {parts[3].strip()}", "%m/%d/%Y %H:%M"
            ).replace(tzinfo=timezone.utc)
            val_str = parts[4].strip()
            if not val_str or val_str in ("M", "R", "P"):
                continue
            rows.append((dt, float(val_str)))
        except (ValueError, IndexError):
            continue
    return sorted(rows, key=lambda r: r[0])


async def fetch_c16_runoff(client: httpx.AsyncClient) -> RunoffData:
    """Fetch S-41 discharge (cfs) and 24-hour rainfall from DBHYDRO."""
    start_date, end_date = _date_window()
    c16_flow: Optional[float] = None
    rain_mm: Optional[float] = None
    timestamp: Optional[datetime] = None
    errors: list[str] = []

    # Flow at S-41
    try:
        params = {
            **_BASE_PARAMS,
            "v_start_date": start_date,
            "v_end_date": end_date,
            "v_station_list": "S41",
            "v_data_type_list": "FLOW",
        }
        resp = await client.get(_DBHYDRO_BASE, params=params, timeout=15.0)
        resp.raise_for_status()
        rows = _parse_dbhydro_csv(resp.text)
        if rows:
            timestamp, c16_flow = rows[-1]
            logger.info("S-41 flow: %.1f cfs at %s", c16_flow, timestamp)
        else:
            logger.warning("S-41 DBHYDRO returned no rows")
    except Exception as exc:
        errors.append(f"S41 flow: {exc}")
        logger.error("S41 flow fetch failed: %s", exc)

    # Rainfall (sum last 24h, inches -> mm)
    try:
        params = {
            **_BASE_PARAMS,
            "v_start_date": start_date,
            "v_end_date": end_date,
            "v_station_list": _RAIN_STATION,
            "v_data_type_list": "RAIN",
        }
        resp = await client.get(_DBHYDRO_BASE, params=params, timeout=15.0)
        resp.raise_for_status()
        rows = _parse_dbhydro_csv(resp.text)
        if rows:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)
            total_in = sum(v for dt, v in rows if dt >= cutoff)
            rain_mm = round(total_in * 25.4, 2)
            logger.info("24h rain: %.1f mm", rain_mm)
    except Exception as exc:
        errors.append(f"Rain: {exc}")
        logger.error("Rain fetch failed: %s", exc)

    intensity: Optional[str] = None
    if c16_flow is not None:
        intensity = "high" if c16_flow >= 1500 else ("med" if c16_flow >= 400 else "low")

    return RunoffData(
        recent_rain_mm=rain_mm,
        c16_flow_cfs=c16_flow,
        runoff_intensity=intensity,
        timestamp=timestamp,
        error=(" | ".join(errors) if errors else None),
    )
