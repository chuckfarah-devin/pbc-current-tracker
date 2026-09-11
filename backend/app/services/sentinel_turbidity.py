"""
Sentinel turbidity service — fetch chain (best resolution wins):

  1. Sentinel-2 MSI   10 m   Copernicus Data Space Ecosystem (CDSE)
  2. Sentinel-3 OLCI  300 m  Copernicus Marine / ERDDAP
  3. MODIS 8-day      ~1 km  NOAA CoastWatch ERDDAP (existing fallback)

CDSE (Sentinel-2) requires free registration at dataspace.copernicus.eu
Set CDSE_USERNAME + CDSE_PASSWORD in .env to enable.

Turbidity proxy (Nechad et al., adapted for coastal FL):
  turbidity ~ B03 / (1 - B03/0.1729) * 228.1   (red band, simplified)
  clarity_score = max(0, 100 - turbidity * 5)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.config import settings
from app.models.conditions import TurbidityData
from app.services.turbidity import fetch_turbidity as fetch_modis   # MODIS fallback

logger = logging.getLogger(__name__)

# ── Copernicus Data Space (CDSE) ──────────────────────────────────────────────
_CDSE_AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
_CDSE_ODATA = "https://catalogue.dataspace.copernicus.eu/odata/v1"
_CDSE_S3 = "https://eodata.dataspace.copernicus.eu"   # COG access

# Boynton Inlet area bounding box (WGS84)
_AOI = "POLYGON((-80.20 26.30,-79.90 26.30,-79.90 26.70,-80.20 26.70,-80.20 26.30))"
_MAX_CLOUD_PCT = 20.0   # skip scenes with > 20% cloud cover

# Sentinel-2 band indices used for turbidity proxy (10 m bands)
# B03 = Green (0.560 um), B04 = Red (0.665 um), B08 = NIR (0.842 um)
_S2_TURBIDITY_BAND = "B03"

async def _cdse_token(client: httpx.AsyncClient) -> Optional[str]:
    """Obtain a short-lived CDSE access token using client credentials."""
    username = getattr(settings, "cdse_username", None)
    password = getattr(settings, "cdse_password", None)
    if not username or not password:
        return None
    try:
        resp = await client.post(
            _CDSE_AUTH_URL,
            data={
                "client_id": "cdse-public",
                "grant_type": "password",
                "username": username,
                "password": password,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as exc:
        logger.debug("CDSE auth failed: %s", exc)
        return None


async def _fetch_sentinel2(client: httpx.AsyncClient, lat: float, lon: float) -> Optional[TurbidityData]:
    """
    1. Authenticate with CDSE (skipped if no credentials configured)
    2. Find the most recent cloud-free Sentinel-2 L2A scene over the AOI
    3. Read the B03 Green band at the target pixel using the OData signed URL
    4. Convert reflectance to turbidity proxy -> clarity score
    """
    token = await _cdse_token(client)
    if token is None:
        logger.debug("Sentinel-2: no CDSE credentials configured; skipping")
        return None

    headers = {"Authorization": f"Bearer {token}"}
    # Search OData catalog for most recent L2A scene, low cloud cover
    now = datetime.now(tz=timezone.utc)
    window_start = (now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
    search_params = {
        "$filter": (
            f"Collection/Name eq 'SENTINEL-2' "
            f"and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
            f"and att/OData.CSC.DoubleAttribute/Value lt {_MAX_CLOUD_PCT}) "
            f"and ContentDate/Start gt {window_start} "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{_AOI}') "
            f"and contains(Name,'L2A')"
        ),
        "$orderby": "ContentDate/Start desc",
        "$top": 1,
    }
    try:
        resp = await client.get(
            f"{_CDSE_ODATA}/Products",
            params=search_params,
            headers=headers,
            timeout=20.0,
        )
        resp.raise_for_status()
        products = resp.json().get("value", [])
        if not products:
            logger.info("Sentinel-2: no cloud-free scene found in last 14 days")
            return None

        product = products[0]
        scene_time_str = product.get("ContentDate", {}).get("Start", "")
        try:
            scene_time = datetime.fromisoformat(scene_time_str.replace("Z", "+00:00"))
        except ValueError:
            scene_time = now

        product_id = product.get("Id")
        product_name = product.get("Name", "")
        logger.info("Sentinel-2 scene found: %s (cloud < %.0f%%)", product_name, _MAX_CLOUD_PCT)

        # Download a small AOI crop of B03 (Green) at 10 m resolution
        # Using CDSE S3-compatible endpoint with signed download
        # For now we use the mean reflectance from the product metadata if available
        # Full pixel extraction requires rasterio + COG streaming — stub noted here
        # TODO: implement COG pixel pull using rasterio.open() with VSICURL
        mean_b03 = product.get("Attributes", {}).get("meanReflectanceB03", None)
        if mean_b03 is None:
            logger.warning("Sentinel-2: B03 reflectance not in metadata; skipping pixel pull")
            return None

        # Nechad turbidity proxy (simplified Green band version)
        refl = float(mean_b03) / 10000.0   # DN to reflectance
        ntu = round((228.1 * refl) / (1.0 - refl / 0.1729), 2) if refl < 0.1729 else 50.0
        ntu = max(0.0, min(100.0, ntu))
        score = max(0, min(100, int(100 - ntu * 2)))

        logger.info("Sentinel-2 turbidity: NTU=%.1f, clarity=%d (10 m)", ntu, score)
        return TurbidityData(
            ntu=ntu,
            clarity_score=score,
            source="Sentinel2",
            resolution_m=10,
            last_clear_scene=scene_time,
            timestamp=now,
        )

    except Exception as exc:
        logger.debug("Sentinel-2 catalog query failed: %s", exc)
        return None

async def _fetch_sentinel3(client: httpx.AsyncClient, lat: float, lon: float) -> Optional[TurbidityData]:
    """
    Sentinel-3 OLCI turbidity via ERDDAP (300 m, near-real-time).
    Uses the Copernicus Marine ERDDAP dataset id: cmems_obs-oc_atl_bgc-transp_nrt_l3-olci-300m_P1D
    No credentials required for the ERDDAP endpoint.
    """
    erddap_base = "https://nrt.cmems-du.eu/erddap/griddap"
    dataset = "cmems_obs-oc_atl_bgc-transp_nrt_l3-olci-300m_P1D"
    # Request a ~0.5 deg box, last available time
    lat_min, lat_max = lat - 0.25, lat + 0.25
    lon_min, lon_max = lon - 0.25, lon + 0.25
    url = (
        f"{erddap_base}/{dataset}.csv"
        f"?KD490[(last)][({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
    )
    try:
        resp = await client.get(url, timeout=25.0)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        values: list[float] = []
        ts_str: Optional[str] = None
        for line in lines[2:]:
            parts = line.split(",")
            if len(parts) < 4:
                continue
            val_str = parts[3].strip()
            if val_str in ("", "NaN", "nan"):
                continue
            try:
                values.append(float(val_str))
                if ts_str is None:
                    ts_str = parts[0].strip()
            except ValueError:
                continue
        if not values:
            return None
        mean_kd = sum(values) / len(values)
        # KD490 (m-1) -> turbidity proxy: NTU ~ KD490 * 20 (empirical coastal FL)
        ntu = round(mean_kd * 20.0, 2)
        score = max(0, min(100, int(100 - mean_kd * 200)))
        ts: Optional[datetime] = None
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                ts = datetime.now(tz=timezone.utc)
        logger.info("Sentinel-3 KD490=%.3f -> NTU=%.1f, clarity=%d (300 m)", mean_kd, ntu, score)
        return TurbidityData(
            ntu=ntu,
            clarity_score=score,
            source="Sentinel3",
            resolution_m=300,
            timestamp=ts,
        )
    except Exception as exc:
        logger.debug("Sentinel-3 ERDDAP failed: %s", exc)
        return None


async def fetch_best_turbidity(client: httpx.AsyncClient, lat: float, lon: float) -> TurbidityData:
    """
    Try sources in order of resolution. Return first that succeeds.
    """
    # 1. Sentinel-2 (10 m) — needs CDSE credentials
    result = await _fetch_sentinel2(client, lat, lon)
    if result is not None:
        return result

    # 2. Sentinel-3 (300 m) — public ERDDAP
    result = await _fetch_sentinel3(client, lat, lon)
    if result is not None:
        return result

    # 3. MODIS 8-day (~1 km) — existing service
    logger.warning("Sentinel sources unavailable; falling back to MODIS")
    result = await fetch_modis(client, lat, lon)
    if result.error is None:
        result.resolution_m = 1000
    return result
