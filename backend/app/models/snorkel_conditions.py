from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LocationInfo(BaseModel):
    lat: float
    lon: float
    label: str = "Boynton Inlet"


class CameraHealthObservation(BaseModel):
    camera_id: str
    location: str
    view: Optional[str] = None
    page_url: Optional[str] = None
    source_url: Optional[str] = None
    fetched_at: Optional[datetime] = None
    observed_at: Optional[datetime] = None
    observed_at_local: Optional[str] = None
    freshness: Optional[str] = None
    age_minutes: Optional[float] = None
    local_conditions_verified: bool = False
    status: str
    error: Optional[str] = None
    visual_flags: list[str] = []
    image_url: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    mean_brightness: Optional[float] = None
    limitations: list[str] = []


class WaterColourSample(BaseModel):
    region: str
    bounds: list[float] = []
    warm_percent: float
    blue_green_percent: float
    other_percent: float
    mean_rgb: list[float] = []
    pixels: int


class WaterAppearanceObservation(BaseModel):
    camera_id: str
    location: str
    headline: str
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    fetched_at: Optional[datetime] = None
    observed_at: Optional[datetime] = None
    observed_at_local: Optional[str] = None
    samples: list[WaterColourSample] = []
    framing_verified: bool = False
    current_direction: Optional[str] = None
    underwater_visibility: Optional[str] = None
    status: str
    limitations: list[str] = []


class WindObservation(BaseModel):
    time_utc: Optional[datetime] = None
    time_local: Optional[str] = None
    speed_kn: Optional[float] = None
    speed_mph: Optional[float] = None
    gust_kn: Optional[float] = None
    gust_mph: Optional[float] = None
    from_degrees: Optional[float] = None
    from_compass: Optional[str] = None
    toward_degrees: Optional[float] = None
    toward_compass: Optional[str] = None
    preferred: bool = False
    preferred_label: Optional[str] = None
    status: str


class RainWindow(BaseModel):
    date: Optional[str] = None
    label: Optional[str] = None
    start_utc: Optional[datetime] = None
    end_utc: Optional[datetime] = None
    mm: Optional[float] = None
    inches: Optional[float] = None
    category: Optional[str] = None
    status: str = "available"


class WeatherObservation(BaseModel):
    reference_time_utc: Optional[datetime] = None
    reference_time_local: Optional[str] = None
    source: Optional[str] = None
    recent_24h: RainWindow = Field(default_factory=RainWindow)
    forward_24h: RainWindow = Field(default_factory=RainWindow)
    wind: WindObservation = Field(default_factory=lambda: WindObservation(status="unknown"))
    daily_outlook: list[RainWindow] = []
    limitations: list[str] = []


class AlgaeRegion(BaseModel):
    name: str
    status: str
    image_url: Optional[str] = None
    colored_pixels_pct_of_recognized_water: Optional[float] = None
    recognized_water_pixels_pct: Optional[float] = None
    requested_bounds_wsen: list[float] = []
    crop_ltrb_exclusive: list[int] = []
    interpretation: str


class AlgaeObservation(BaseModel):
    source_filename: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    product: Optional[str] = None
    composite: Optional[str] = None
    nominal_resolution_m: Optional[int] = None
    source_url: Optional[str] = None
    source_image_url: Optional[str] = None
    source_legend_url: Optional[str] = None
    source_bounds_wsen: list[float] = []
    regions: list[AlgaeRegion] = []
    limitations: list[str] = []


class C16Observation(BaseModel):
    live_flow: Optional[str] = None
    info_url: str = "https://www.sfwmd.gov/"
    notes: str = "Live discharge is not measured here."


class SurfaceMotionObservation(BaseModel):
    developer_only: bool = True
    observed_at: Optional[datetime] = None
    regions_image_url: Optional[str] = None
    clip_url: Optional[str] = None
    user_label: Optional[str] = None
    automated_observation: Optional[str] = None
    interpretation: str
    status: str
    limitations: list[str] = []


class SnorkelConditionsResponse(BaseModel):
    generated_at_utc: datetime
    mode: str
    mode_disclaimer: str
    location: LocationInfo
    cameras: list[CameraHealthObservation] = []
    water_appearance: list[WaterAppearanceObservation] = []
    weather: Optional[WeatherObservation] = None
    algae: Optional[AlgaeObservation] = None
    c16: C16Observation = Field(default_factory=C16Observation)
    surface_motion: Optional[SurfaceMotionObservation] = None
    limitations: list[str] = []
