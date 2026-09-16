"""GET /api/snorkel-conditions — recorded replay or live fetch from the devin-handoff PoCs."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Request

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


def _live_dir() -> Path:
    return Path(settings.poc_handoff_dir) / "live-check"


def _load_json(name: str, source_dir: Path | None = None) -> dict[str, Any] | None:
    source_dir = source_dir or _handoff_demo()
    path = source_dir / name / "result.json"
    if not path.exists():
        logger.warning("Missing fixture: %s", path)
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


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _parse_camera(
    cam: dict[str, Any],
    base: str,
    source_dir: Path,
    image_prefix: str,
) -> CameraHealthObservation:
    image_file = cam.get("image_file")
    image_url = None
    if image_file and (source_dir / "camera" / image_file).exists():
        image_url = f"{base}/{image_prefix}/camera/{image_file}"

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
        age_minutes=cam.get("age_minutes"),
        local_conditions_verified=cam.get("local_conditions_verified", False),
        status=cam.get("status", "unknown"),
        error=cam.get("error"),
        visual_flags=cam.get("visual_flags", []),
        image_url=image_url,
        image_width=cam.get("width"),
        image_height=cam.get("height"),
        mean_brightness=cam.get("mean_brightness"),
        limitations=limitations,
    )


def _build_camera_health(
    base: str,
    source_dir: Path = _handoff_demo(),
    image_prefix: str = "fixtures",
) -> list[CameraHealthObservation]:
    data = _load_json("camera", source_dir)
    if not data:
        return []
    return [_parse_camera(cam, base, source_dir, image_prefix) for cam in data.get("cameras", [])]


def _build_appearance(
    health_by_id: dict[str, CameraHealthObservation],
    base: str,
    source_dir: Path = _handoff_demo(),
    image_prefix: str = "fixtures",
    framing_verified: bool = True,
    status_label: str = "recorded; manual review needed",
) -> list[WaterAppearanceObservation]:
    data = _load_json("appearance", source_dir)
    if not data:
        return []

    results: list[WaterAppearanceObservation] = []
    for item in data.get("results", []):
        camera_id = item.get("camera", "unknown")
        health = health_by_id.get(camera_id)

        if framing_verified:
            image_url = None
            jpg = source_dir / "appearance" / f"{camera_id}.jpg"
            if jpg.exists():
                image_url = f"{base}/{image_prefix}/appearance/{camera_id}.jpg"
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
            headline = item.get("headline", "")
        else:
            # Framing is not validated for live: show the raw camera view for visual review.
            image_url = None
            samples = []
            observed_local = health.observed_at_local if health else None
            headline = "Framing not verified · no colour claim"

        limitations = [data.get("method", "")] if data.get("method") else []
        if framing_verified:
            limitations.append("ROI manually selected; pan or framing change requires review.")
        else:
            limitations.append("Camera framing is not verified. Regions need human review before any colour claim.")

        results.append(
            WaterAppearanceObservation(
                camera_id=camera_id,
                location=item.get("location", "unknown"),
                headline=headline,
                source_url=item.get("source_url"),
                image_url=image_url,
                fetched_at=health.fetched_at if health else None,
                observed_at=health.observed_at if health else None,
                observed_at_local=observed_local,
                samples=samples,
                framing_verified=framing_verified,
                current_direction=item.get("current_direction"),
                underwater_visibility=item.get("underwater_visibility"),
                status=status_label,
                limitations=limitations,
            )
        )
    return results


def _build_weather(source_dir: Path = _handoff_demo()) -> WeatherObservation | None:
    data = _load_json("weather", source_dir)
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


def _build_algae(
    base: str,
    source_dir: Path = _handoff_demo(),
    image_prefix: str = "fixtures",
) -> AlgaeObservation | None:
    data = _load_json("sargassum", source_dir)
    if not data:
        return None

    regions = []
    for name, region in data.get("regions", {}).items():
        image_url = None
        png = source_dir / "sargassum" / f"{name}.png"
        if png.exists():
            image_url = f"{base}/{image_prefix}/sargassum/{name}.png"

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
        source_image_url=src.get("image_url"),
        source_legend_url=src.get("legend_url"),
        source_bounds_wsen=data.get("source_bounds_wsen", []),
        regions=regions,
        limitations=[
            data.get("freshness", ""),
            "Sargassum status is a rendered-image color match; not measured density, biomass or beach severity.",
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
        user_label="Likely northward · recorded reference, not live",
        automated_observation="Leftward ripple/reflection movement in the recorded northward reference clip.",
        interpretation=(
            "Recorded reference only; this is not a live camera reading. "
            "The reference demonstrates northward surface flow in the three reflection patches. "
            "No measured speed; validate live examples before relying on the indicator."
        ),
        status="experimental; recorded reference",
        limitations=[
            "Reference clip only; validate orientation, texture and south/weak/panning examples before live use.",
            "Do not use sign agreement alone as confidence.",
        ],
    )


def _build_surface_motion(
    base: str,
    source_dir: Path,
    image_prefix: str = "fixtures",
) -> SurfaceMotionObservation | None:
    data = _load_json("motion", source_dir)
    if not data:
        return None

    image_url = None
    jpg = source_dir / "motion" / "regions.jpg"
    if jpg.exists():
        image_url = f"{base}/{image_prefix}/motion/regions.jpg"

    observed_at = data.get("observed_at")
    fetched_at = data.get("classified_at_utc")
    try:
        observed_at_dt = datetime.fromisoformat(observed_at) if observed_at else None
    except ValueError:
        observed_at_dt = None
    try:
        fetched_at_dt = datetime.fromisoformat(fetched_at) if fetched_at else None
    except ValueError:
        fetched_at_dt = None

    return SurfaceMotionObservation(
        developer_only=True,
        observed_at=observed_at_dt,
        fetched_at=fetched_at_dt,
        regions_image_url=image_url,
        clip_url=data.get("source_url"),
        user_label=data.get("user_label"),
        automated_observation=data.get("automated_observation"),
        interpretation=data.get(
            "interpretation",
            "Surface motion is experimental; no current speed or safety inference.",
        ),
        status=data.get("status", "unclear"),
        limitations=[
            "Experimental optical-flow reading, not a measured current.",
            "Assumes fixed camera orientation matching the recorded northward reference.",
        ],
    )


def _run_poc(script: str, args: list[str], timeout: int) -> tuple[bool, str]:
    """Run a single PoC script and return (ok, error_or_log_tail).

    Prefer the repository-maintained copy, falling back to the handoff package.
    """
    repo_path = Path(settings.poc_repo_dir) / script
    handoff_path = Path(settings.poc_handoff_dir) / script
    script_path = repo_path if repo_path.exists() else handoff_path
    cmd = [sys.executable, str(script_path), *args]
    logger.info("Running %s", " ".join(cmd))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"{script} timed out after {timeout}s"
    if r.returncode != 0:
        tail = (r.stdout + "\n" + r.stderr).strip().splitlines()[-10:]
        return False, f"{script} failed: {'; '.join(tail) or 'non-zero exit'}"
    return True, r.stdout.strip().splitlines()[-1] if r.stdout else "ok"


def _discover_latest_sargassum(live_dir: Path, max_lookback: int = 5) -> tuple[bool, str]:
    """Try today, then the previous days, for the most recent valid 7-day composite."""
    today = date.today()
    for i in range(max_lookback):
        day = today - timedelta(days=i)
        out = live_dir / "sargassum_search" / day.isoformat()
        out.mkdir(parents=True, exist_ok=True)
        ok, _ = _run_poc(
            "floating_sargassum_card_poc.py",
            ["--date", day.isoformat(), "--period", "7DAY", "--output", str(out)],
            timeout=90,
        )
        if ok:
            # Make the successful result available at a stable path.
            target = live_dir / "sargassum"
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(out, target)
            return True, f"USF composite ending {day.isoformat()}"
    # If nothing worked but we have a previous cached composite, use it as a dated cache.
    if (live_dir / "sargassum" / "result.json").exists():
        return False, "No recent composite found; using cached result"
    return False, f"No valid USF composite in the last {max_lookback} days"


def _update_live_sources(live_dir: Path) -> dict[str, tuple[bool, str]]:
    """Run the independent live PoCs and return per-source (ok, message_or_error)."""
    live_dir.mkdir(parents=True, exist_ok=True)

    camera_ok, camera_err = _run_poc(
        "beach_camera_health_poc.py",
        ["--output", str(live_dir / "camera"), "--fresh-minutes", "360"],
        timeout=180,
    )

    appearance_ok, appearance_err = False, "camera not ready"
    if camera_ok and (live_dir / "camera" / "result.json").exists():
        appearance_ok, appearance_err = _run_poc(
            "camera_water_appearance_poc.py",
            ["--input", str(live_dir / "camera"), "--output", str(live_dir / "appearance")],
            timeout=60,
        )

    weather_ok, weather_err = _run_poc(
        "rainfall_forecast_poc.py",
        [
            "--output",
            str(live_dir / "weather"),
            "--latitude",
            str(settings.inlet_lat),
            "--longitude",
            str(settings.inlet_lon),
        ],
        timeout=90,
    )

    sargassum_ok, sargassum_err = _discover_latest_sargassum(live_dir)

    # Surface flow from the captured Delray .ts
    motion_ok, motion_err = False, "camera not ready"
    delray_checked_at = None
    delray_page_url = ""
    if camera_ok and (live_dir / "camera" / "result.json").exists():
        try:
            camera_data = json.loads(
                (live_dir / "camera" / "result.json").read_text(encoding="utf-8")
            )
            for cam in camera_data.get("cameras", []):
                if cam.get("id") == "delray":
                    delray_checked_at = cam.get("checked_at")
                    delray_page_url = cam.get("page_url", "")
                    break
        except Exception:
            pass
    if delray_checked_at and (live_dir / "camera" / "delray_sample.ts").exists():
        # Never keep a stale motion result; a failed run leaves the directory empty.
        if (live_dir / "motion").exists():
            shutil.rmtree(live_dir / "motion", ignore_errors=True)
        motion_ok, motion_err = _run_poc(
            "delray_surface_flow_poc.py",
            [
                "--input",
                str(live_dir / "camera" / "delray_sample.ts"),
                "--observed-at",
                delray_checked_at,
                "--source-url",
                delray_page_url,
                "--output",
                str(live_dir / "motion"),
            ],
            timeout=120,
        )

    return {
        "camera": (camera_ok, camera_err),
        "appearance": (appearance_ok, appearance_err),
        "weather": (weather_ok, weather_err),
        "sargassum": (sargassum_ok, sargassum_err),
        "motion": (motion_ok, motion_err),
    }


def _build_live_conditions(base: str) -> SnorkelConditionsResponse:
    """Assemble the live/cached conditions payload."""
    now = datetime.now(timezone.utc)
    live_dir = _live_dir()
    live_dir.mkdir(parents=True, exist_ok=True)

    source_status = _update_live_sources(live_dir)

    cameras = _build_camera_health(base, live_dir, "fixtures/live")
    if not source_status["camera"][0]:
        for cam in cameras:
            cam.status = "cached"
            cam.error = (
                (cam.error or "") + " Live camera fetch failed: " + source_status["camera"][1]
            ).strip()

    health_by_id = {c.camera_id: c for c in cameras}

    appearance: list[WaterAppearanceObservation] = []
    if (live_dir / "appearance" / "result.json").exists():
        appearance = _build_appearance(
            health_by_id,
            base,
            source_dir=live_dir,
            image_prefix="fixtures/live",
            framing_verified=False,
            status_label="framing_unverified",
        )
    if not source_status["appearance"][0]:
        for a in appearance:
            a.status = "framing_unverified"
            a.error = (
                (a.error or "") + " Live appearance fetch failed: " + source_status["appearance"][1]
            ).strip()

    weather = _build_weather(live_dir)
    if weather and not source_status["weather"][0]:
        weather.limitations.append(
            "Live weather fetch failed; showing cached result: " + source_status["weather"][1]
        )

    algae = _build_algae(base, live_dir, "fixtures/live")
    if algae and not source_status["sargassum"][0]:
        algae.limitations.append(
            "Live USF search failed; showing cached result: " + source_status["sargassum"][1]
        )
    if not algae and not source_status["sargassum"][0]:
        logger.warning("Sargassum unavailable: %s", source_status["sargassum"][1])

    surface_motion = _build_surface_motion(base, live_dir, "fixtures/live")

    limitations = [
        "Image colour thresholds are exploratory.",
        "Weather is a model estimate, not a rain gauge.",
        "Sargassum detection is a rendered-image color proxy, not measured biomass or beach severity.",
        "Surface motion is experimental and developer-only.",
        "C-16 live discharge is not measured here.",
        "Live-mode framing is unverified; colour claims are suppressed.",
    ]
    for source, (ok, err) in source_status.items():
        if not ok:
            limitations.append(f"{source}: {err}")

    return SnorkelConditionsResponse(
        generated_at_utc=now,
        mode="live",
        mode_disclaimer=(
            "Live fetch. Each source is fetched independently and carries its own "
            "observed_at timestamp; cached results are used when a live source fails. "
            "Camera framing is not automatically verified, so colour claims are suppressed."
        ),
        location=LocationInfo(lat=26.530, lon=-80.052, label="Boynton Inlet"),
        cameras=cameras,
        water_appearance=appearance,
        weather=weather,
        algae=algae,
        c16=C16Observation(),
        surface_motion=surface_motion,
        limitations=limitations,
    )


@router.get("/snorkel-conditions", response_model=SnorkelConditionsResponse)
async def get_snorkel_conditions(
    request: Request,
    mode: str = Query("recorded_replay", enum=["recorded_replay", "live"]),
) -> SnorkelConditionsResponse:
    base = _base_url(request)

    if mode == "live":
        return _build_live_conditions(base)

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
            "Sargassum detection is a rendered-image color proxy, not measured biomass or beach severity.",
            "Surface motion is experimental and developer-only.",
            "C-16 live discharge is not measured here.",
        ],
    )
