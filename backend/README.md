# Palm Beach Plume Tracker — Backend

FastAPI backend that aggregates nearshore water-quality data for snorkelers and divers around **Boynton Inlet / Lake Worth Lagoon, Florida**.

## Quick start

```bash
cd backend

# First time: create virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt

# Optional: copy config
cp .env.example .env

uvicorn app.main:app --reload --port 8000
```

Interactive API docs: **http://localhost:8000/docs**

## Endpoints

### `GET /api/status`
System health and last-update timestamps for each data source.

### `GET /api/snorkel-conditions`
Recorded replay snapshot from the devin-handoff PoCs:
- **cameras** — source health, timestamps, provenance and status for each camera
- **water_appearance** — headline, colour samples and ROI bounds for reviewed cameras
- **weather** — Open-Meteo wind (FROM direction) and 24-hour rain windows
- **algae** — USF FA/FAD rendered-image proxy with period and legend bounds
- **c16** — SFWMD information link (live discharge not measured)
- **surface_motion** — developer-only reference example, not live

This endpoint is intentionally replay-only; each source keeps its own `observed_at` and is not presented as current.

### `GET /api/conditions?lat={lat}&lon={lon}`
Full conditions snapshot:
- **current** — speed/direction (NOAA CO-OPS, tidal proxy fallback)
- **turbidity** — water clarity score 0–100 (NOAA ERDDAP / MODIS satellite)
- **runoff** — C-16 discharge (cfs) + 24h rainfall (SFWMD DBHYDRO)
- **lake_o** — Lake Okeechobee stage + east-coast structure flows (USACE Hydromet)
- **plume** — dominant source (LakeO / C16_runoff / tidal_local) + direction
- **snorkel_index** — score 0–100 + label (Excellent / Good / Fair / Marginal / Poor)

Default location: Boynton Inlet (26.530, -80.052). All fields degrade gracefully to `null` if a source is unavailable.

## Data sources (all public, no API keys required)

| Source | API |
|---|---|
| Tidal currents | NOAA CO-OPS (`api.tidesandcurrents.noaa.gov`) |
| Water clarity | NOAA CoastWatch ERDDAP (`coastwatch.pfeg.noaa.gov`) |
| C-16 discharge | SFWMD DBHYDRO (`my.sfwmd.gov`) |
| Lake Okeechobee | USACE Hydromet (`apps.saj.usace.army.mil`) |

## Plume classification logic

1. **LakeO** — if east-coast USACE discharge > 500 cfs
2. **C16_runoff** — if S-41 flow > 200 cfs and 24h rain > 10 mm
3. **tidal_local** — all else

## Snorkel index scoring (starts at 100)

| Factor | Max deduction |
|---|---|
| Turbidity / clarity score | −40 |
| Current speed | −25 |
| C-16 / runoff intensity | −20 |
| Lake O influence | −15 |

## Project layout

```
backend/
├── app/
│   ├── main.py          # FastAPI app, CORS, lifespan
│   ├── config.py        # Settings (pydantic-settings)
│   ├── models/
│   │   └── conditions.py  # Pydantic response models
│   ├── routers/
│   │   ├── status.py      # GET /api/status
│   │   └── conditions.py  # GET /api/conditions
│   └── services/
│       ├── cache.py         # In-process TTL cache
│       ├── noaa_currents.py # NOAA CO-OPS client
│       ├── turbidity.py     # ERDDAP MODIS client
│       ├── sfwmd.py         # SFWMD DBHYDRO client
│       ├── usace.py         # USACE Hydromet client
│       └── plume.py         # Plume + snorkel index logic
└── requirements.txt
```
