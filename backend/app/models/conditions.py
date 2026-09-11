from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LocationInfo(BaseModel):
    lat: float
    lon: float


class CurrentData(BaseModel):
    speed_mps: Optional[float] = None
    direction_deg: Optional[float] = None
    source: Optional[str] = None
    resolution_m: Optional[int] = None   # spatial resolution of the source
    timestamp: Optional[datetime] = None
    error: Optional[str] = None


class TurbidityData(BaseModel):
    ntu: Optional[float] = None
    clarity_score: Optional[int] = Field(None, ge=0, le=100)
    source: Optional[str] = None
    resolution_m: Optional[int] = None   # spatial resolution of the source
    last_clear_scene: Optional[datetime] = None  # satellite: last cloud-free pass
    timestamp: Optional[datetime] = None
    error: Optional[str] = None


class RunoffData(BaseModel):
    recent_rain_mm: Optional[float] = None
    c16_flow_cfs: Optional[float] = None
    runoff_intensity: Optional[str] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None


class LakeOStructures(BaseModel):
    S308: Optional[float] = None
    S80: Optional[float] = None
    S351: Optional[float] = None
    S352: Optional[float] = None
    S354: Optional[float] = None


class LakeOData(BaseModel):
    lake_stage_ft: Optional[float] = None
    east_discharge_cfs_total: Optional[float] = None
    structures: LakeOStructures = LakeOStructures()
    lake_o_influence: Optional[str] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None


class PlumeData(BaseModel):
    direction_deg: Optional[float] = None
    speed_mps: Optional[float] = None
    source: Optional[str] = None            # LakeO / C16_runoff / tidal_local
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    resolution: Optional[str] = None        # macro / meso / micro


class SargassumData(BaseModel):
    density_class: Optional[int] = Field(None, ge=0, le=4)
    presence: Optional[bool] = None       # True if density_class >= 2
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    source: Optional[str] = None          # USF_GCOOS
    resolution_m: Optional[int] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None


class SnorkelIndex(BaseModel):
    score: int = Field(..., ge=0, le=100)
    label: str                               # Excellent/Good/Fair/Marginal/Poor
    reasons: list[str] = []


class ConditionsResponse(BaseModel):
    location: LocationInfo
    current: CurrentData
    turbidity: TurbidityData
    runoff: RunoffData
    lake_o: LakeOData
    plume: PlumeData
    snorkel_index: SnorkelIndex
    nearshore_quality: Optional[str] = None  # excellent / good / fair / poor
    sargassum: Optional[SargassumData] = None  # Phase 2 — USF GCOOS


class SourceStatus(BaseModel):
    last_update: Optional[datetime] = None
    status: str = "unknown"
    error: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    last_update: datetime
    sources: dict[str, SourceStatus]
