from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Path to the extracted PoC handoff package for recorded-replay mode
    poc_handoff_dir: str = (
        r"C:\Users\chuck\PBC Snorkel conditions\PBC-Snorkel-Devin-Handoff\devin-handoff"
    )
    replay_demo_dir: str = "demo"


settings = Settings()
