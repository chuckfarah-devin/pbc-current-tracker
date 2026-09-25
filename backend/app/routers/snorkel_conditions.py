"""GET /api/snorkel-conditions — recorded replay or live fetch from the devin-handoff PoCs."""
from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
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
_refresh_task: asyncio.Task | None = None
_refresh_started_at: datetime | None = None


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

    limitations = list(cam.get("limitations", []))
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
        location="Delray Beach",
        direction="northward",
        evidence_strength="likely",
        freshness="recorded",
        orientation_verified=True,
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

    observed_at_dt = _parse_dt(data.get("observed_at"))
    retrieved_at_dt = _parse_dt(data.get("retrieved_at"))
    analyzed_at_dt = _parse_dt(data.get("analyzed_at") or data.get("classified_at_utc"))

    return SurfaceMotionObservation(
        developer_only=True,
        location="Delray Beach",
        acquisition_id=data.get("acquisition_id"),
        observed_at=observed_at_dt,
        retrieved_at=retrieved_at_dt,
        analyzed_at=analyzed_at_dt,
        fetched_at=analyzed_at_dt,
        direction=data.get("direction", "unknown"),
        evidence_strength=data.get("evidence_strength", "unable"),
        freshness=data.get("freshness", "unknown"),
        reason=data.get("reason") or data.get("automated_observation"),
        orientation_verified=data.get("orientation_verified", False),
        regions_image_url=image_url,
        clip_url=data.get("source_url"),
        user_label=data.get("user_label"),
        automated_observation=data.get("automated_observation"),
        interpretation=data.get("interpretation", "Surface motion is experimental; no current speed or safety inference."),
        status=data.get("status", "unable_to_assess"),
        limitations=[
            "Experimental optical-flow reading, not a measured current.",
            "Direction thresholds are provisional and calibrated from one northward reference.",
        ],
    )


def _build_surface_motion_placeholder(
    refresh_running: bool,
    source_status_motion: tuple[bool, str],
    cameras: list[CameraHealthObservation],
) -> SurfaceMotionObservation:
    """Return a motion observation when no live result file has been published yet.

    Keeps the tile actionable on Android by always supplying a clip_url when a
    Delray camera link is available.
    """
    delray_page = next((c.page_url for c in cameras if c.camera_id == "delray"), None)
    delray_source = next((c.source_url for c in cameras if c.camera_id == "delray"), None)
    clip_url = delray_page or delray_source

    base_limitations = [
        "Experimental optical-flow reading, not a measured current.",
        "Direction thresholds are provisional and calibrated from one northward reference.",
    ]

    if refresh_running:
        return SurfaceMotionObservation(
            developer_only=True,
            location="Delray Beach",
            clip_url=clip_url,
            direction="unknown",
            evidence_strength="pending",
            freshness="pending",
            status="checking",
            reason="Motion analysis is in progress...",
            interpretation="Surface-motion analysis is currently running. Results will appear when the Delray clip has been downloaded, decoded, and analyzed.",
            limitations=base_limitations,
        )

    if source_status_motion[0]:
        # A refresh completed and reported motion success, yet no result file exists.
        reason = "Motion analysis completed but did not produce a result."
    else:
        reason = source_status_motion[1] or "No live Delray motion analysis is available."

    return SurfaceMotionObservation(
        developer_only=True,
        location="Delray Beach",
        clip_url=clip_url,
        direction="unknown",
        evidence_strength="unable",
        freshness="unavailable",
        status="unable_to_assess",
        reason=reason,
        interpretation="Surface-motion analysis was unavailable. No direction or current speed is inferred.",
        limitations=base_limitations + [f"Experimental surface-motion source unavailable: {reason}"],
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


def _eligible_delray_motion(delray: dict[str, Any] | None, clip: Path) -> tuple[bool, str]:
    if not delray or delray.get("status") != "stream_advancing_capture_unverified":
        return False, "current Delray acquisition unavailable"
    acquisition_id = delray.get("acquisition_id")
    if not acquisition_id or not clip.exists():
        return False, "current Delray acquisition has no identified clip"
    actual_hash = hashlib.sha256(clip.read_bytes()).hexdigest()
    if actual_hash != acquisition_id:
        return False, "Delray clip hash does not match the current acquisition"
    return True, ""


def _update_live_sources(live_dir: Path, publish=None) -> dict[str, tuple[bool, str]]:
    """Run independent PoCs; publish each completed source without waiting for motion."""
    live_dir.mkdir(parents=True, exist_ok=True)
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    weather_future = pool.submit(
        _run_poc, "rainfall_forecast_poc.py",
        ["--output", str(live_dir / "weather"), "--latitude", str(settings.inlet_lat), "--longitude", str(settings.inlet_lon)], 90,
    )
    sargassum_future = pool.submit(_discover_latest_sargassum, live_dir)

    camera_ok, camera_err = _run_poc(
        "beach_camera_health_poc.py",
        ["--output", str(live_dir / "camera"), "--fresh-minutes", "360"],
        timeout=180,
    )
    if camera_ok and publish:
        publish("camera")

    appearance_ok, appearance_err = False, "camera not ready"
    if camera_ok and (live_dir / "camera" / "result.json").exists():
        appearance_ok, appearance_err = _run_poc(
            "camera_water_appearance_poc.py",
            ["--input", str(live_dir / "camera"), "--output", str(live_dir / "appearance")],
            timeout=60,
        )
        if appearance_ok and publish:
            publish("appearance")

    # Surface flow is eligible only when this camera acquisition published a decoded Delray clip.
    motion_ok, motion_err = False, "current Delray acquisition unavailable"
    delray = None
    if camera_ok and (live_dir / "camera" / "result.json").exists():
        try:
            camera_data = json.loads((live_dir / "camera" / "result.json").read_text(encoding="utf-8"))
            delray = next((cam for cam in camera_data.get("cameras", []) if cam.get("id") == "delray"), None)
        except (OSError, ValueError):
            delray = None
    clip = live_dir / "camera" / "delray_sample.ts"
    eligible, motion_err = _eligible_delray_motion(delray, clip)
    if eligible:
        acquisition_id = delray["acquisition_id"]
        motion_args = [
            "--input", str(clip), "--retrieved-at", delray.get("retrieved_at") or delray["checked_at"],
            "--acquisition-id", acquisition_id, "--source-url", delray.get("page_url", ""),
            "--output", str(live_dir / "motion"),
        ]
        if delray.get("capture_utc"):
            motion_args.extend(["--observed-at", delray["capture_utc"]])
        motion_ok, motion_err = _run_poc("delray_surface_flow_poc.py", motion_args, timeout=180)
        if motion_ok and publish:
            publish("motion")

    weather_ok, weather_err = weather_future.result()
    if weather_ok and publish:
        publish("weather")
    sargassum_ok, sargassum_err = sargassum_future.result()
    if sargassum_ok and publish:
        publish("sargassum")
    pool.shutdown(wait=True)

    return {
        "camera": (camera_ok, camera_err),
        "appearance": (appearance_ok, appearance_err),
        "weather": (weather_ok, weather_err),
        "sargassum": (sargassum_ok, sargassum_err),
        "motion": (motion_ok, motion_err),
    }


def _publish_source_atomically(staging: Path, live_dir: Path, source: str) -> None:
    source_dir = staging / source
    if not source_dir.exists():
        return
    target = live_dir / source
    target.mkdir(parents=True, exist_ok=True)
    files = sorted(source_dir.rglob("*"), key=lambda p: p.name == "result.json")
    for path in files:
        if not path.is_file():
            continue
        destination = target / path.relative_to(source_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        shutil.copy2(path, temporary)
        temporary.replace(destination)


def _refresh_live_sources(live_dir: Path) -> None:
    staging = live_dir.parent / f"live-staging-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    try:
        statuses = _update_live_sources(staging, lambda source: _publish_source_atomically(staging, live_dir, source))
        status_file = live_dir / "refresh_status.json"
        temporary = status_file.with_suffix(".tmp")
        temporary.write_text(json.dumps({"completed_at": datetime.now(timezone.utc).isoformat(), "sources": statuses}), encoding="utf-8")
        temporary.replace(status_file)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


async def _start_refresh(live_dir: Path) -> None:
    global _refresh_task, _refresh_started_at
    if _refresh_task and not _refresh_task.done():
        return
    _refresh_started_at = datetime.now(timezone.utc)
    _refresh_task = asyncio.create_task(asyncio.to_thread(_refresh_live_sources, live_dir))


def _build_live_conditions(base: str) -> SnorkelConditionsResponse:
    """Assemble promptly from atomically published live/cached observations."""
    now = datetime.now(timezone.utc)
    live_dir = _live_dir()
    live_dir.mkdir(parents=True, exist_ok=True)
    source_status = {name: (False, "not yet refreshed") for name in ("camera", "appearance", "weather", "sargassum", "motion")}
    last_refresh_completed = None
    try:
        published_status = json.loads((live_dir / "refresh_status.json").read_text(encoding="utf-8"))
        source_status.update({name: (bool(value[0]), str(value[1])) for name, value in published_status.get("sources", {}).items()})
        last_refresh_completed = _parse_dt(published_status.get("completed_at"))
    except (OSError, ValueError, TypeError, IndexError):
        pass

    refresh_running = _refresh_task is not None and not _refresh_task.done()

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
    if surface_motion and not source_status["motion"][0]:
        surface_motion.freshness = "cached"
        surface_motion.limitations.append("Current Delray analysis failed; showing the previous result with its original timestamps: " + source_status["motion"][1])
    elif not surface_motion:
        surface_motion = _build_surface_motion_placeholder(
            refresh_running, source_status["motion"], cameras
        )

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
        refresh_status="running" if _refresh_task and not _refresh_task.done() else "idle",
        refresh_started_at=_refresh_started_at,
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
    refresh: bool = Query(False),
) -> SnorkelConditionsResponse:
    base = _base_url(request)

    if mode == "live":
        if refresh:
            await _start_refresh(_live_dir())
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
