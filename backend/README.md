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

### `GET /api/snorkel-conditions?mode=recorded_replay|live`
Combined snorkel-conditions snapshot. Default `mode` is `recorded_replay`.

**`recorded_replay`**: static demo from the devin-handoff PoCs; each source keeps its own `observed_at`.

**`live`**: fetches each source independently from the handoff live PoCs, retaining cached results when a source fails and never substituting the recorded demo:
- **cameras** — source health, timestamps, provenance, `age_minutes` and status
- **water_appearance** — shown for visual review only; colour samples suppressed until framing is verified
- **weather** — Open-Meteo wind (FROM direction) and 24-hour rain windows
- **algae** — USF FA/FAD rendered-image proxy; exact composite period from a bounded search
- **c16** — SFWMD information link (live discharge not measured)
- **surface_motion** — developer-only reference example, not live

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
│   │   ├── conditions.py        # Pydantic response models for /api/conditions
│   │   └── snorkel_conditions.py # Pydantic models for /api/snorkel-conditions
│   ├── routers/
│   │   ├── status.py            # GET /api/status
│   │   ├── conditions.py        # GET /api/conditions
│   │   └── snorkel_conditions.py # GET /api/snorkel-conditions
│   └── services/
│       ├── cache.py         # In-process TTL cache
│       ├── noaa_currents.py # NOAA CO-OPS client
│       ├── turbidity.py     # ERDDAP MODIS client
│       ├── sfwmd.py         # SFWMD DBHYDRO client
│       ├── usace.py         # USACE Hydromet client
│       └── plume.py         # Plume + snorkel index logic
└── requirements.txt
```
