from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Default paths are relative to this file so the repo is portable.
# Override with a .env file (see .env.example) or environment variables.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_ROOT = _REPO_ROOT / "backend"
_HANDOFF_SIBLING = _REPO_ROOT.parent / "PBC Snorkel conditions" / "PBC-Snorkel-Devin-Handoff" / "devin-handoff"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    cache_ttl_seconds: int = 1800
    log_level: str = "INFO"

    # Default location: Boynton Inlet / Lake Worth Lagoon
    inlet_lat: float = 26.530
    inlet_lon: float = -80.052

    # SFWMD station IDs
    sfwmd_c16_station: str = "S41"

    # USACE structure IDs
    usace_structures: list[str] = ["S308", "S80", "S351", "S352", "S354"]

    # Plume classification thresholds
    lake_o_discharge_threshold_cfs: float = 500.0
    c16_flow_threshold_cfs: float = 200.0
    c16_rain_threshold_mm: float = 10.0

    # SFWMD Hydro Data Service (gated) — request via datarequests@sfwmd.gov
    sfwmd_client_id: str = ""
    sfwmd_client_secret: str = ""

    # Optional API keys for higher-resolution sources (v0.2)
    windy_api_key: str = ""        # free key: windy.com/en/api
    cdse_username: str = ""        # free account: dataspace.copernicus.eu
    cdse_password: str = ""        # Sentinel-2 access

    # Path to the extracted PoC handoff package for recorded-replay fixtures.
    # Set PBC_HANDOFF_DIR in your .env if the sibling-folder default does not match.
    poc_handoff_dir: str = str(_HANDOFF_SIBLING)
    replay_demo_dir: str = "demo"

    # Path to the maintained PoCs bundled in this repository.
    poc_repo_dir: str = str(_BACKEND_ROOT / "poc")


settings = Settings()
