# Palm Beach Plume Tracker - Technical Specification

**Version:** 0.2
**Date:** 2026-09-11
**Status:** Ready for Development
**Authors:** Chuck + Copilot + Devin

---

## 1. Purpose

Provide snorkelers and divers with real-time nearshore water conditions around Boynton Inlet / Lake Worth Lagoon, including:

- Nearshore currents (target: within ~100 yards / 90 m)
- Water clarity at 10 m resolution (Sentinel-2)
- Turbidity and NTU estimate
- Plume direction and source
- Snorkel suitability index 0-100

---

## 2. System Overview

```
External Data Sources (all public; Windy requires free API key)
  NOAA CO-OPS  |  NWPS ERDDAP  |  HYCOM THREDDS  |  Windy API
  SFWMD DBHYDRO  |  USACE Hydromet
  Sentinel-2 MSI (10 m)  |  Sentinel-3 OLCI (300 m)  |  MODIS 8-day
         |
         +------------------------------------------+
                              |
                  FastAPI Backend (Python 3.11)
                  GET /api/status
                  GET /api/conditions
                  TTL cache 30 min
                              |
                      JSON over HTTPS
                              |
                  Android App (Kotlin MVVM)
                  Map | Details Panel | Settings
```

---
## 3. Backend

### 3.1 Stack

| Component   | Choice              |
|-------------|---------------------|
| Language    | Python 3.11+        |
| Framework   | FastAPI 0.115       |
| HTTP client | httpx (async)       |
| Validation  | Pydantic v2         |
| Cache       | cachetools TTLCache |
| Server      | Uvicorn             |

### 3.2 Directory Layout

```
backend/
+- app/
   +- main.py
   +- config.py
   +- models/
   |   +- conditions.py          # Updated: resolution_m, plume.resolution
   +- routers/
   |   +- status.py
   |   +- conditions.py
   +- services/
       +- cache.py
       +- noaa_currents.py        # Tidal fallback only
       +- hycom_currents.py       # NEW: NWPS > HYCOM > Windy > CO-OPS
       +- turbidity.py            # MODIS fallback only
       +- sentinel_turbidity.py   # NEW: Sentinel-2 > S-3 > MODIS
       +- sfwmd.py
       +- usace.py
       +- plume.py                # Updated: resolution field
```

### 3.3 API Endpoints

#### GET /api/status
System health + last data-fetch timestamps. Status: ok (< 2h), stale (> 2h), unknown.

#### GET /api/conditions?lat={lat}&lon={lon}
All sources fetched concurrently. Any failure = null + error string. Always HTTP 200.
Default: Boynton Inlet (26.530, -80.052).

**Response Fields (v0.2 additions in bold)**

| Field                           | Type   | Description                           |
|---------------------------------|--------|---------------------------------------|
| current.speed_mps               | float  | Water current speed m/s               |
| current.direction_deg           | float  | Direction degrees oceanographic       |
| current.source                  | string | NWPS / HYCOM / Windy / NOAA_COOPS    |
| **current.resolution_m**        | int    | Spatial resolution in metres          |
| turbidity.clarity_score         | int    | 0-100 water clarity score             |
| turbidity.ntu                   | float  | Estimated NTU                         |
| turbidity.source                | string | Sentinel2 / Sentinel3 / NOAA_MODIS   |
| **turbidity.resolution_m**      | int    | Spatial resolution in metres          |
| runoff.c16_flow_cfs             | float  | S-41 structure flow cfs               |
| runoff.recent_rain_mm           | float  | 24h rainfall total mm                 |
| runoff.runoff_intensity         | string | low / med / high                      |
| lake_o.east_discharge_cfs_total | float  | S-80+S-351+S-352+S-354 cfs           |
| lake_o.lake_stage_ft            | float  | Lake Okeechobee water level ft        |
| plume.source                    | string | LakeO / C16_runoff / tidal_local      |
| plume.confidence                | float  | 0.0-1.0                               |
| **plume.resolution**            | string | macro / meso / micro                  |
| snorkel_index.score             | int    | Composite suitability 0-100           |
| snorkel_index.label             | string | Excellent/Good/Fair/Marginal/Poor     |
| snorkel_index.reasons           | list   | Human-readable reason strings         |
| **nearshore_quality**           | string | excellent / good / fair / poor        |
### 3.4 Data Sources (v0.2)

#### HYCOM + NWPS Nearshore Currents (hycom_currents.py) -- NEW

Fetch chain (highest resolution wins):

| Priority | Source          | Resolution | Endpoint                                         |
|----------|-----------------|------------|--------------------------------------------------|
| 1        | NWPS ERDDAP     | ~750 m     | coastwatch.pfeg.noaa.gov/erddap/griddap/nwpsModel|
| 2        | HYCOM GLBy0.08  | ~8 km      | tds.hycom.org/thredds/dodsC/GLBy0.08/latest      |
| 3        | Windy API       | ~9 km      | api.windy.com/api/point-forecast/v2              |
| 4        | NOAA CO-OPS     | Point/tidal| api.tidesandcurrents.noaa.gov (existing fallback)|

Notes:
- NWPS: NOAA Nearshore Wave Prediction System on ERDDAP, no key required
- HYCOM: Global ocean model via THREDDS/OPeNDAP, no key required
- Windy: Free API key required (register at windy.com/en/api); set WINDY_API_KEY env var
- All sources degrade gracefully; best available resolution is reported

Output:
```json
{
  "speed_mps": 0.22,
  "direction_deg": 175,
  "source": "NWPS",
  "resolution_m": 750
}
```

#### Sentinel-2 Turbidity (sentinel_turbidity.py) -- NEW

Fetch chain:

| Priority | Source         | Resolution | Access                                    |
|----------|----------------|------------|-------------------------------------------|
| 1        | Sentinel-2 MSI | 10 m       | Copernicus Data Space (CDSE STAC API)     |
| 2        | Sentinel-3 OLCI| 300 m      | Copernicus Marine / ERDDAP                |
| 3        | MODIS 8-day    | ~1 km      | NOAA CoastWatch ERDDAP (existing)         |

Notes:
- Sentinel-2: Uses CDSE (dataspace.copernicus.eu) STAC API + OData. Free registration required.
  Set CDSE_USERNAME and CDSE_PASSWORD env vars. Band math: NDWI / B03/B08 turbidity proxy.
- Sentinel-3: Near-real-time OLCI product, 300 m, available via Copernicus Marine or ERDDAP.
- Cloud cover limitation: Sentinel optical sensors cannot see through clouds.
  System reports last_clear_scene timestamp so user knows data age.

Output:
```json
{
  "ntu": 4.2,
  "clarity_score": 72,
  "resolution_m": 10,
  "source": "Sentinel2",
  "last_clear_scene": "2026-09-10T13:22:00Z"
}
```

#### NOAA CO-OPS Tidal Currents (noaa_currents.py) -- Fallback Only
Unchanged from v0.1. Used only when NWPS/HYCOM/Windy all fail.

#### SFWMD DBHYDRO C-16 (sfwmd.py) -- Unchanged
#### USACE Hydromet Lake O (usace.py) -- Unchanged

### 3.5 Updated Plume Classification

```
Priority 1 - Lake O (macro scale):
  if east_discharge >= 500 cfs:
      source     = LakeO
      confidence = 0.60 + east_discharge/5000  (max 0.95)
      resolution = macro

Priority 2 - C-16 Runoff (meso scale):
  elif c16_flow >= 200 AND rain >= 10 mm:
      source     = C16_runoff
      confidence = 0.55 + c16_flow/3000  (max 0.90)
      resolution = meso

Priority 3 - Nearshore Drift (micro scale):
  elif current.resolution_m <= 100:
      source     = tidal_local
      confidence = 0.80
      resolution = micro

Default:
  source     = tidal_local
  confidence = 0.70
  resolution = macro
```

### 3.6 Snorkel Index (unchanged from v0.1)
Starts at 100, deducts for turbidity, current speed, runoff intensity, Lake O influence.

### 3.7 Nearshore Quality Field (NEW)

Derived from current resolution and turbidity resolution:

| Condition                                        | nearshore_quality |
|--------------------------------------------------|-------------------|
| current.resolution_m <= 100 AND clarity >= 60    | excellent         |
| current.resolution_m <= 1000 AND clarity >= 40   | good              |
| current.resolution_m <= 9000 AND clarity >= 20   | fair              |
| Otherwise                                        | poor              |

### 3.8 Caching
TTL = 1800 s (30 min). Key: conditions_{lat:.2f}_{lon:.2f}. Configurable via CACHE_TTL_SECONDS.

---

## 4. Android App

### 4.1 Stack

| Component    | Choice                       |
|--------------|------------------------------|
| Language     | Kotlin                       |
| Architecture | MVVM (ViewModel + StateFlow) |
| Networking   | Retrofit 2 + OkHttp + Moshi  |
| Map          | Mapbox Maps SDK for Android  |
| Min SDK      | API 26 (Android 8.0)         |

### 4.2 Screens (v0.2)

**Home / Map Screen**
- Mapbox map centred on Boynton Inlet (26.530, -80.052)
- Snorkel index badge top-centre (green/yellow/orange/red)
- Resolution badge: [Nearshore Accuracy: 10 m] or [750 m] or [~8 km]
- Arrow overlay: current direction + speed
- Sentinel-2 clarity raster layer (10 m, semi-transparent blue-to-brown heat map)
- Plume direction arrow + source label
- Manual refresh FAB

**Conditions Details Panel (bottom sheet)**
- Current: speed, direction, source, resolution badge
- Clarity: score bar, NTU, source, resolution badge, last clear scene timestamp
- Runoff: C-16 flow, 24h rain, intensity chip
- Lake O: stage, east discharge, per-structure breakdown
- Plume: source chip, confidence %, resolution (macro/meso/micro)
- Nearshore quality summary chip
- Data-unavailable callouts for any null source

**Settings Screen**
- Speed units: m/s vs knots
- Rain units: mm vs inches
- Backend URL
- Windy API key entry
- CDSE credentials entry (for Sentinel-2)
- Saved favourite spots

---

## 5. Environment Variables (.env)

```
# Cache
CACHE_TTL_SECONDS=1800
LOG_LEVEL=INFO

# Windy API (free key from windy.com/en/api)
WINDY_API_KEY=your_key_here

# Copernicus Data Space (free registration at dataspace.copernicus.eu)
CDSE_USERNAME=your_email
CDSE_PASSWORD=your_password

# Inlet default location
INLET_LAT=26.530
INLET_LON=-80.052
```

---

## 6. Non-Functional Requirements

| Requirement       | Target                                              |
|-------------------|-----------------------------------------------------|
| API response time | < 3 seconds (all sources concurrent)                |
| Cache hit latency | < 100 ms                                            |
| Data freshness    | 30-min TTL; app pulls on open + manual              |
| Resilience        | Any source failure = partial response, never crash  |
| Distribution      | Personal / small group; no auth required initially  |
| Battery           | No continuous polling; WorkManager 30 min           |

---

## 7. Known Limitations

| Item                           | Notes                                                         |
|--------------------------------|---------------------------------------------------------------|
| Sentinel-2 cloud cover         | Cannot see through clouds; reports last_clear_scene age       |
| NWPS shoreline mask            | May not resolve currents right at the beach/inlet             |
| HYCOM smoothing                | 8-km model smooths out small-scale features                   |
| Windy requires free API key    | User must register and set WINDY_API_KEY env var              |
| CDSE requires free account     | Sentinel-2 access needs CDSE_USERNAME/CDSE_PASSWORD           |
| USACE Hydromet undocumented    | Endpoint found via network inspection; may change             |
| Single inlet focus             | Extend to Jupiter, Hobe Sound, Lake Worth Inlet               |

---

## 8. Development Phases

### Backend

| Phase | Scope                                                       | Status  |
|-------|-------------------------------------------------------------|----------|
| 1     | Skeleton: /api/status, /api/conditions, models, cache        | Done    |
| 2     | SFWMD C-16 + rainfall, NOAA currents, USACE Lake O           | Done    |
| 3     | HYCOM/NWPS nearshore currents, Sentinel-2/3 turbidity        | Done    |
| 4     | Sargassum module: USF Marine Optics Lab / GCOOS (stub ready) | Pending |

### Android

| Version | Scope                                                         | Status   |
|---------|---------------------------------------------------------------|----------|
| v1 MVP  | Map, current arrows, clarity layer, plume overlay, snorkel index | Up next  |
| v1 MVP  | Conditions details panel, settings screen, WorkManager refresh | Pending  |
| v1 MVP  | Visual polish, snorkel index tuning, field testing             | Pending  |
| v2      | Sargassum map heatmap layer (toggle)                          | Pending  |
| v2      | Sargassum details panel block                                 | Pending  |

---

---

## Appendix A -- Backend Phase 4 + Android v2: Sargassum Tracking Module

**Backend:** Stub in services/sargassum.py. Full integration = Backend Phase 4.
**Android:** Sargassum UI (map layer + details panel) = Android v2. Not in v1 MVP.

### A.1 Purpose

Detect daily sargassum seaweed presence near Boynton Inlet using satellite imagery
from the USF Marine Optics Lab. Sargassum mats significantly reduce snorkel suitability
and are a growing seasonal concern in SE Florida.

### A.2 Data Source

**USF Marine Optics Lab / GCOOS**
URL: https://optics.marine.usf.edu/cgi-bin/optics_data?sortby=Class&roi=GCOOS&Date=YYYY/MM/DD
- Daily MODIS-based classification, ~1 km resolution
- Density classes 0-4 with cloud mask
- Typically published by 14:00 UTC for the previous satellite pass

### A.3 Density Classes

| Class | Label          | Meaning                              |
|-------|----------------|--------------------------------------|
| 0     | None detected  | No sargassum in pixel                |
| 1     | Very low       | Sparse; possible false positive      |
| 2     | Low-moderate   | Patchy surface mats (presence=true)  |
| 3     | Moderate-high  | Dense mats, likely visible           |
| 4     | Very high      | Thick continuous coverage            |

Presence threshold: class >= 2.

### A.4 New Response Field

```json
"sargassum": {
  "density_class": 2,
  "presence": true,
  "confidence": 0.78,
  "source": "USF_GCOOS",
  "resolution_m": 1000,
  "timestamp": "2026-09-10T14:00:00Z"
}
```

Field is `null` while Phase 2 is not yet implemented. The stub already wires the
field into `/api/conditions` so no breaking changes are needed when Phase 2 ships.

### A.5 Snorkel Index Integration (Phase 2)

Additional deductions when sargassum is added:

| Condition                  | Deduction |
|----------------------------|-----------|
| density_class 2 (presence) | -10       |
| density_class 3            | -20       |
| density_class 4            | -30       |

### A.6 Android v2 UI Additions

**Map toggle**
- Checkbox: [x] Sargassum layer
- Heatmap: transparent (0) -> yellow (1) -> orange (2) -> red (3) -> dark red (4)
- Or simplified "presence zone" outline polygon

**Details panel addition**
```
Sargassum
  Density:    Moderate (Class 2)
  Confidence: 78%
  Note: Offshore mats detected, check nearshore conditions
```

### A.7 Implementation Tasks

- [ ] Parse USF GCOOS CSV format (confirm exact column schema)
- [ ] Handle date rollover when daily composite not yet published
- [ ] Implement `_parse_usf_response()` in `services/sargassum.py`
- [ ] Replace stub body in `fetch_sargassum()` with real implementation
- [ ] Add sargassum deductions to `compute_snorkel_index()` in `plume.py`
- [ ] Android: map heatmap layer with toggle
- [ ] Android: details panel sargassum block


---
*End of specification v0.2*
