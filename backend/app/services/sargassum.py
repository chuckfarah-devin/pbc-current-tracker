"""
Sargassum Tracking Service — PHASE 2 PLACEHOLDER
=================================================

Source:  USF Marine Optics Lab / GCOOS
URL:     https://optics.marine.usf.edu/cgi-bin/optics_data
         ?sortby=Class&roi=GCOOS&Date=YYYY/MM/DD

Data provided:
  - Daily sargassum density classification (Class 0-4)
  - Cloud mask (affects confidence)
  - Pixel lat/lon grid (~1 km resolution, MODIS-based)

Density classes:
  0  No sargassum detected
  1  Very low (sparse, possible false positive)
  2  Low-moderate (patchy surface mats)
  3  Moderate-high (dense mats, likely visible)
  4  Very high (thick continuous coverage)

Presence threshold: class >= 2

Implementation notes for Phase 2:
  1. Parse the USF endpoint CSV/text response to extract the classification grid
  2. Find the pixel nearest to the user lat/lon
  3. Use the cloud mask coverage to derive confidence
  4. Fall back gracefully if the daily composite isn't yet available
     (USF typically publishes by ~14:00 UTC for the previous pass)

TODO Phase 2:
  [ ] Confirm exact CSV column format from USF endpoint
  [ ] Handle date rollover (if today's composite not yet published, use yesterday)
  [ ] Add sargassum presence to snorkel index deduction (-10 if present, -20 if dense)
  [ ] Android: heatmap layer (Class 0=transparent, 1=yellow, 2=orange, 3=red, 4=dark red)
  [ ] Android: Details panel note ("Offshore mats detected ~X km from shore")
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.models.conditions import SargassumData

logger = logging.getLogger(__name__)

_USF_BASE = "https://optics.marine.usf.edu/cgi-bin/optics_data"

# Density class -> human label
_CLASS_LABELS = {
    0: "None detected",
    1: "Very low",
    2: "Low-moderate",
    3: "Moderate-high",
    4: "Very high",
}


def _nearest_pixel(grid: list[dict], lat: float, lon: float) -> Optional[dict]:
    """Return the grid pixel dict nearest to (lat, lon)."""
    if not grid:
        return None
    return min(
        grid,
        key=lambda p: (p["lat"] - lat) ** 2 + (p["lon"] - lon) ** 2,
    )


async def fetch_sargassum(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
    date: Optional[datetime] = None,
) -> SargassumData:
    """
    Fetch the daily sargassum classification for the given lat/lon.

    This is a PHASE 2 STUB — it logs a clear message and returns a
    SargassumData with error='Phase 2 not yet implemented' so the API
    responds cleanly without crashing.

    When Phase 2 is ready, replace the stub body with the real implementation.
    """
    logger.info(
        "Sargassum service called for %.4f, %.4f — Phase 2 stub, returning None",
        lat, lon,
    )

    # ── STUB ── When Phase 2 is implemented, replace everything below ─────────
    # Expected implementation sketch:
    #
    #   if date is None:
    #       date = datetime.now(tz=timezone.utc)
    #   date_str = date.strftime("%Y/%m/%d")
    #   params = {"sortby": "Class", "roi": "GCOOS", "Date": date_str}
    #   resp = await client.get(_USF_BASE, params=params, timeout=20.0)
    #   resp.raise_for_status()
    #   grid = _parse_usf_response(resp.text)   # TODO: implement parser
    #   pixel = _nearest_pixel(grid, lat, lon)
    #   if pixel is None:
    #       return SargassumData(error="No data for location")
    #   density_class = int(pixel["class"])
    #   cloud_fraction = float(pixel.get("cloud_mask", 0.5))
    #   confidence = round(1.0 - cloud_fraction, 2)
    #   return SargassumData(
    #       density_class=density_class,
    #       presence=density_class >= 2,
    #       confidence=confidence,
    #       source="USF_GCOOS",
    #       resolution_m=1000,
    #       timestamp=date,
    #   )
    # ── END STUB ──────────────────────────────────────────────────────────────

    return SargassumData(
        density_class=None,
        presence=None,
        confidence=None,
        source="USF_GCOOS",
        resolution_m=1000,
        timestamp=None,
        error="Phase 2 not yet implemented",
    )
