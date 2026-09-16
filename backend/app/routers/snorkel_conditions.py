"""GET /api/snorkel-conditions — recorded replay from the devin-handoff PoCs."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from app.config import settings
from app.models.snorkel_conditions import (
    AlgaeObservation,
    AlgaeRegion,
    CameraHealthObservation,
    C16Observation,
    LocationInfo,
    RainWindow,
    SnorkelConditionsResponse,
    SurfaceMotionObservation,
    WaterAppearanceObservation,
    WaterColourSample,
    WeatherObservation,
    WindObservation,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _handoff_demo() -> Path:
    return Path(settings.poc_handoff_dir) / settings.replay_demo_dir


def _load_json(name: str) -> dict[str, Any] | None:
    path = _handoff_demo() / name / "result.json"
    if not path.exists():
        logger.warning("Missing replay fixture: %s", path)
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _wind_preference(w: dict[str, Any]) -> tuple[bool, str]:
    speed = w.get("speed_kn")
    gust = w.get("gust_kn")
    bearing = w.get("from_degrees")
    mph = None if speed is None else speed * 1.150779448
    gust_mph = None if gust is None else round(gust * 1.150779448, 1)
    favorable = (
        mph is not None
        and 0 < mph < 10
        and bearing is not None
        and 247.5 <= bearing < 292.5
    )
    label = (
        "Light west wind · preferred local pattern"
        if favorable
        else "Check wind alongside the camera"
    )
    return favorable, label


def _parse_camera(cam: dict[str, Any], base: str) -> CameraHealthObservation:
    image_file = cam.get("image_file")
    image_url = None
    if image_file and (_handoff_demo() / "camera" / image_file).exists():
        image_url = f"{base}/fixtures/camera/{image_file}"

    limitations = []
    if cam.get("visual_review"):
        limitations.append(cam["visual_review"])
    if cam.get("capture_time_basis"):
        limitations.append(f"Capture time basis: {cam['capture_time_basis']}")

    return CameraHealthObservation(
        camera_id=cam.get("id", "unknown"),
        location=cam.get("location", "unknown"),
        view=cam.get("view"),
        page_url=cam.get("page_url"),
        source_url=cam.get("image_url"),
        fetched_at=_parse_dt(cam.get("checked_at")),
        observed_at=_parse_dt(cam.get("capture_utc")),
        observed_at_local=cam.get("provider_label"),
        freshness=cam.get("freshness"),
        status=cam.get("status", "unknown"),
        error=cam.get("error"),
        visual_flags=cam.get("visual_flags", []),
        image_url=image_url,
        image_width=cam.get("width"),
        image_height=cam.get("height"),
        mean_brightness=cam.get("mean_brightness"),
        limitations=limitations,
    )


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _build_camera_health(base: str) -> list[CameraHealthObservation]:
    data = _load_json("camera")
    if not data:
        return []
    return [_parse_camera(cam, base) for cam in data.get("cameras", [])]


def _build_appearance(
    health_by_id: dict[str, CameraHealthObservation], base: str
) -> list[WaterAppearanceObservation]:
    data = _load_json("appearance")
    if not data:
        return []

    results: list[WaterAppearanceObservation] = []
    for item in data.get("results", []):
        camera_id = item.get("camera", "unknown")
        health = health_by_id.get(camera_id)
        image_url = None
        jpg = _handoff_demo() / "appearance" / f"{camera_id}.jpg"
        if jpg.exists():
            image_url = f"{base}/fixtures/appearance/{camera_id}.jpg"

        samples = [
            WaterColourSample(
                region=s.get("region", ""),
                bounds=s.get("bounds", []),
                warm_percent=s.get("warm_percent", 0.0),
                blue_green_percent=s.get("blue_green_percent", 0.0),
                other_percent=s.get("other_percent", 0.0),
                mean_rgb=s.get("mean_rgb", []),
                pixels=s.get("pixels", 0),
            )
            for s in item.get("samples", [])
        ]

        observed_local = item.get("timestamp")
        limitations = [data.get("method", "")] if data.get("method") else []
        limitations.append("ROI manually selected; pan or framing change requires review.")

        results.append(
            WaterAppearanceObservation(
                camera_id=camera_id,
                location=item.get("location", "unknown"),
                headline=item.get("headline", ""),
                source_url=item.get("source_url"),
                image_url=image_url,
                fetched_at=health.fetched_at if health else None,
                observed_at=health.observed_at if health else None,
                observed_at_local=observed_local,
                samples=samples,
                current_direction=item.get("current_direction"),
                underwater_visibility=item.get("underwater_visibility"),
                status="recorded; manual review needed",
                limitations=limitations,
            )
        )
    return results


def _build_weather() -> WeatherObservation | None:
    data = _load_json("weather")
    if not data:
        return None

    w = data.get("wind_now", {})
    favorable, pref_label = _wind_preference(w)
    wind = WindObservation(
        time_utc=_parse_dt(w.get("time_utc")),
        time_local=None,
        speed_kn=w.get("speed_kn"),
        speed_mph=w.get("speed_mph"),
        gust_kn=w.get("gust_kn"),
        gust_mph=round(w.get("gust_kn") * 1.150779448, 1) if w.get("gust_kn") is not None else None,
        from_degrees=w.get("from_degrees"),
        from_compass=w.get("from_compass"),
        toward_degrees=w.get("toward_degrees"),
        toward_compass=w.get("toward_compass"),
        preferred=favorable,
        preferred_label=pref_label,
        status=w.get("status", "unknown"),
    )

    def rain(item: dict[str, Any]) -> RainWindow:
        return RainWindow(
            date=item.get("date"),
            label=item.get("label"),
            start_utc=_parse_dt(item.get("start_utc")),
            end_utc=_parse_dt(item.get("end_utc")),
            mm=item.get("mm"),
            inches=item.get("inches"),
            category=item.get("category"),
            status=item.get("status", "available"),
        )

    recent = data.get("recent_24h", {})
    forward = data.get("forward_24h", {})
    outlook = [rain(d) for d in data.get("daily_outlook", [])]

    return WeatherObservation(
        reference_time_utc=_parse_dt(data.get("reference_time_utc")),
        reference_time_local=None,
        source=data.get("source"),
        recent_24h=rain(recent),
        forward_24h=rain(forward),
        wind=wind,
        daily_outlook=outlook,
        limitations=[
            data.get("runoff_impact", ""),
            data.get("category_note", ""),
            "Wind is a 10 m model estimate; direction is FROM.",
        ],
    )


def _build_algae(base: str) -> AlgaeObservation | None:
    data = _load_json("sargassum")
    if not data:
        return None

    regions = []
    for name, region in data.get("regions", {}).items():
        image_url = None
        png = _handoff_demo() / "sargassum" / f"{name}.png"
        if png.exists():
            image_url = f"{base}/fixtures/sargassum/{name}.png"

        regions.append(
            AlgaeRegion(
                name=name.replace("_", " ").title(),
                status=region.get("status", "unknown"),
                image_url=image_url,
                colored_pixels_pct_of_recognized_water=region.get(
                    "colored_pixels_pct_of_recognized_water"
                ),
                recognized_water_pixels_pct=region.get("recognized_water_pixels_pct"),
                requested_bounds_wsen=region.get("requested_bounds_wsen", []),
                crop_ltrb_exclusive=region.get("crop_ltrb_exclusive", []),
                interpretation=region.get(
                    "interpretation",
                    "Color matches are an exploratory rendered-image proxy.",
                ),
            )
        )

    src = data.get("source", {})
    return AlgaeObservation(
        source_filename=src.get("filename"),
        period_start=src.get("period_start"),
        period_end=src.get("period_end"),
        product=src.get("product"),
        composite=src.get("composite"),
        nominal_resolution_m=src.get("nominal_resolution_m"),
        source_url=src.get("page_url"),
        source_bounds_wsen=data.get("source_bounds_wsen", []),
        regions=regions,
        limitations=[
            data.get("freshness", ""),
            "Palette fractions are not algae density/biomass or beach severity.",
        ],
    )


def _build_motion(base: str) -> SurfaceMotionObservation | None:
    data = _load_json("motion")
    if not data:
        return None

    image_url = None
    jpg = _handoff_demo() / "motion" / "regions.jpg"
    if jpg.exists():
        image_url = f"{base}/fixtures/motion/regions.jpg"

    return SurfaceMotionObservation(
        developer_only=True,
        regions_image_url=image_url,
        clip_url=None,
        user_label="Likely northward · user-confirmed example",
        automated_observation="Leftward ripple/reflection movement in three patches.",
        interpretation=(
            "Automated observation: leftward ripple/reflection movement. "
            "User field interpretation: northward surface flow. "
            "No measured speed; not a current live reading."
        ),
        status="experimental; developer-only",
        limitations=[
            "Reference clip only; validate orientation, texture and south/weak/panning examples before live use.",
            "Do not use sign agreement alone as confidence.",
        ],
    )


@router.get("/snorkel-conditions", response_model=SnorkelConditionsResponse)
async def get_snorkel_conditions(request: Request) -> SnorkelConditionsResponse:
    base = _base_url(request)
    now = datetime.now(timezone.utc)

    cameras = _build_camera_health(base)
    health_by_id = {c.camera_id: c for c in cameras}
    appearance = _build_appearance(health_by_id, base)
    weather = _build_weather()
    algae = _build_algae(base)
    motion = _build_motion(base)

    return SnorkelConditionsResponse(
        generated_at_utc=now,
        mode="recorded_replay",
        mode_disclaimer=(
            "Recorded replay from mixed sources. Each observation carries its own "
            "observed_at timestamp; these are not simultaneous or current conditions."
        ),
        location=LocationInfo(lat=26.530, lon=-80.052, label="Boynton Inlet"),
        cameras=cameras,
        water_appearance=appearance,
        weather=weather,
        algae=algae,
        c16=C16Observation(),
        surface_motion=motion,
        limitations=[
            "Image colour thresholds are exploratory.",
            "Weather is a model estimate, not a rain gauge.",
            "Algae is a rendered-image proxy, not biomass or beach severity.",
            "Surface motion is experimental and developer-only.",
            "C-16 live discharge is not measured here.",
        ],
    )
