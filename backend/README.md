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

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Use `--host 0.0.0.0` so phones on the same Wi-Fi can reach the server. If you only need local development, you can omit `--host`.

Interactive API docs: **http://localhost:8000/docs**

### Connecting an Android phone

1. Make sure the PC and phone are on the same Wi-Fi network.
2. Find the PC's local IP address:
   ```powershell
   Get-NetIPAddress -AddressFamily IPv4 |
       Where-Object {$_.IPAddress -like "192.168*" -or $_.IPAddress -like "10.*" -or $_.IPAddress -like "172.*"} |
       Select-Object IPAddress, InterfaceAlias
   ```
3. In the app, go to **Settings → Data source → Live** and enter:
   ```
   http://<pc-ip>:8000
   ```
   For example: `http://192.168.1.249:8000`
4. If the phone cannot connect, check Windows Firewall and allow Python to accept incoming connections on private networks.

## Endpoints

### `GET /api/status`
System health and last-update timestamps for each data source.

### `GET /api/snorkel-conditions?mode=recorded_replay|live`
Combined snorkel-conditions snapshot. Default `mode` is `recorded_replay`.

**`recorded_replay`**: static demo from the devin-handoff PoCs; each source keeps its own `observed_at`.

**`live`**: fetches each source independently from the repository-maintained PoCs in `backend/poc/`, retaining cached results when a source fails and never substituting the recorded demo:
- **cameras** — source health, timestamps, provenance, `age_minutes` and status
- **water_appearance** — shown for visual review only; colour samples suppressed until framing is verified
- **weather** — Open-Meteo wind (FROM direction) and 24-hour rain windows
- **sargassum** — USF FA/FAD rendered-image color proxy; exact 7-day composite period from a bounded search
- **c16** — SFWMD information link (live discharge not measured)
- **surface_flow** — experimental Delray optical-flow indicator: likely northward, likely southward, or unclear; no current speed

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
