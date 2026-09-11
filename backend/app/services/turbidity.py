"""
Turbidity / water-clarity via NOAA CoastWatch ERDDAP.

Dataset: erdMH1chla8day (MODIS Aqua 8-day chlorophyll-a)
Bounding box: 0.4-degree square centred on Boynton Inlet.
Clarity score: 100 = crystal clear, 0 = opaque (empirical, coastal SE FL).
NTU estimate:  ntu = chl_a * 1.5 (rough proxy for nearshore turbid water).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.models.conditions import TurbidityData

logger = logging.getLogger(__name__)
_ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
_DATASET = "erdMH1chla8day"
_LAT_MIN, _LAT_MAX = 26.3, 26.7
_LON_MIN, _LON_MAX = -80.2, -79.9


def _chl_to_clarity(chl: float) -> tuple[float, int]:
    ntu = round(chl * 1.5, 2)
    score = max(0, min(100, int(100 - chl * 5)))
    return ntu, score


async def fetch_turbidity(client: httpx.AsyncClient, lat: float, lon: float) -> TurbidityData:
    url = (
        f"{_ERDDAP}/{_DATASET}.csv"
        f"?chlorophyll[(last)][({_LAT_MIN}):1:({_LAT_MAX})][({_LON_MIN}):1:({_LON_MAX})]"
    )
    try:
        resp = await client.get(url, timeout=30.0)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        values: list[float] = []
        timestamp_str: Optional[str] = None
        for line in lines[2:]:   # skip header + units rows
            parts = line.split(",")
            if len(parts) < 5:
                continue
            chl_str = parts[4].strip()
            if chl_str in ("", "NaN", "nan"):
                continue
            try:
                values.append(float(chl_str))
                if timestamp_str is None:
                    timestamp_str = parts[0].strip()
            except ValueError:
                continue
        if not values:
            return TurbidityData(error="No satellite chlorophyll data for region")
        mean_chl = sum(values) / len(values)
        ntu, score = _chl_to_clarity(mean_chl)
        ts: Optional[datetime] = None
        if timestamp_str:
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                ts = datetime.now(tz=timezone.utc)
        logger.info("ERDDAP chl %.2f mg/m3 (n=%d) -> NTU %.1f, clarity %d",
                    mean_chl, len(values), ntu, score)
        return TurbidityData(ntu=ntu, clarity_score=score, source="NOAA_ERDDAP_MODIS", timestamp=ts)
    except Exception as exc:
        logger.error("Turbidity fetch failed: %s", exc)
        return TurbidityData(error=str(exc))
