"""Delray surface-flow direction POC. Not a current speed or safety measurement.

Uses the recorded northward clip as the reference signature.
Outputs one of: likely northward, likely southward, or unclear.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

BASE_FRAME_SIZE = (1280, 526)
BASE_REGIONS = {
    "Left of reflection": (180, 310, 340, 355),
    "Reflection edge": (370, 315, 490, 355),
    "Right of reflection": (670, 298, 790, 320),
}
MIN_FRAME_SIZE = (640, 240)


def scale_regions(h: int, w: int) -> dict[str, tuple[int, int, int, int]] | None:
    base_w, base_h = BASE_FRAME_SIZE
    scale_x = w / base_w
    scale_y = h / base_h
    if (
        w < MIN_FRAME_SIZE[0]
        or h < MIN_FRAME_SIZE[1]
        or not (0.5 <= scale_x <= 2.0)
        or not (0.5 <= scale_y <= 2.0)
    ):
        return None
    regions = {}
    for name, (x, y, r, t) in BASE_REGIONS.items():
        regions[name] = (
            int(round(x * scale_x)),
            int(round(y * scale_y)),
            int(round(r * scale_x)),
            int(round(t * scale_y)),
        )
    return regions


def read_frames(path, sample_fps=5.0):
    c = cv2.VideoCapture(str(path))
    source_fps = float(c.get(cv2.CAP_PROP_FPS) or 0.0)
    if source_fps <= 0 or source_fps > 120:
        source_fps = 30.0
    step = max(1, round(source_fps / sample_fps))
    frames, times, duplicates = [], [], 0
    index = 0
    previous = None
    while True:
        ok, frame = c.read()
        if not ok:
            break
        if index % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if previous is not None and float(np.mean(cv2.absdiff(previous, gray))) < 0.25:
                duplicates += 1
            else:
                frames.append(frame)
                times.append(index / source_fps)
                previous = gray
        index += 1
    c.release()
    return frames, times, {"source_fps": source_fps, "duplicate_frames": duplicates, "duration_seconds": index / source_fps}


def _camera_offsets(frames):
    offsets = [0.0]
    for a, b in zip(frames, frames[1:]):
        h, w = a.shape[:2]
        aa = cv2.cvtColor(a[: max(1, int(h * 0.30))], cv2.COLOR_BGR2GRAY)
        bb = cv2.cvtColor(b[: max(1, int(h * 0.30))], cv2.COLOR_BGR2GRAY)
        points = cv2.goodFeaturesToTrack(aa, 120, 0.02, 8)
        if points is None or len(points) < 8:
            offsets.append(0.0)
            continue
        moved, status, _ = cv2.calcOpticalFlowPyrLK(aa, bb, points, None)
        valid = status.ravel() == 1
        offsets.append(float(np.median((moved[valid] - points[valid])[:, 0, 0])) if valid.sum() >= 8 else 0.0)
    return np.asarray(offsets[1:], dtype=float)


def analyze(frames, times, regions):
    if len(frames) < 10 or len(times) != len(frames):
        raise ValueError("Insufficient decoded footage")
    camera_dx = _camera_offsets(frames)
    if len(camera_dx) == 0:
        raise ValueError("No consecutive frame intervals")
    if float(np.percentile(np.abs(camera_dx), 90)) > 2.5:
        raise ValueError("Camera pan, zoom, or framing change detected")
    rows = {k: [] for k in regions}
    for i, (a, b) in enumerate(zip(frames, frames[1:])):
        dt = times[i + 1] - times[i]
        if dt <= 0 or dt > 0.75:
            continue
        for name, (x, y, r, t) in regions.items():
            aa = cv2.cvtColor(a[y:t, x:r], cv2.COLOR_BGR2GRAY)
            bb = cv2.cvtColor(b[y:t, x:r], cv2.COLOR_BGR2GRAY)
            texture = float(aa.std())
            if aa.size == 0 or aa.shape != bb.shape or texture < 5.0:
                continue
            flow = cv2.calcOpticalFlowFarneback(aa, bb, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            dx = (float(np.median(flow[:, :, 0])) - camera_dx[i]) * (BASE_FRAME_SIZE[0] / a.shape[1]) / dt
            rows[name].append((times[i], dx, texture, dt))
    result = {}
    for name, vals in rows.items():
        if len(vals) < 8:
            result[name] = {"usable": False, "reason": "insufficient textured intervals", "pair_count": len(vals)}
            continue
        arr = np.asarray([v[1] for v in vals], dtype=float)
        noise = max(0.03, float(np.median(np.abs(arr - np.median(arr)))) * 1.4826)
        directional = arr[np.abs(arr) > noise]
        windows = []
        for start in np.arange(vals[0][0], vals[-1][0] + 0.001, 4.0):
            chunk = np.asarray([v[1] for v in vals if start <= v[0] < start + 4.0])
            if len(chunk) >= 4:
                windows.append(float(np.median(chunk)))
        interval_drift = {}
        sample_times = np.asarray([v[0] for v in vals], dtype=float)
        cumulative = np.cumsum(arr * np.asarray([v[3] for v in vals], dtype=float))
        for target in (0.2, 0.5, 1.0, 2.0):
            estimates = []
            for i, start in enumerate(sample_times):
                j = int(np.searchsorted(sample_times, start + target))
                if j < len(cumulative) and j > i:
                    elapsed = sample_times[j] - start
                    estimates.append(float((cumulative[j] - cumulative[i]) / elapsed))
            interval_drift[f"{target:g}s"] = float(np.median(estimates)) if estimates else None
        result[name] = {
            "usable": len(directional) >= 6 and len(windows) >= 2,
            "median_dx_normalized_px_per_second": float(np.median(arr)),
            "noise_floor_normalized_px_per_second": noise,
            "leftward_agreement": float((directional < 0).mean()) if len(directional) else 0.0,
            "rightward_agreement": float((directional > 0).mean()) if len(directional) else 0.0,
            "interval_drift_normalized_px_per_second": interval_drift,
            "window_medians": windows,
            "pair_count": len(vals),
            "texture_std": float(np.median([v[2] for v in vals])),
        }
    result["camera_check"] = {
        "median_dx_pixels_per_interval": float(np.median(camera_dx)),
        "p90_abs_dx_pixels_per_interval": float(np.percentile(np.abs(camera_dx), 90)),
    }
    return result


def check_framing(frames, regions):
    if not frames:
        raise ValueError("No frames decoded")
    if regions is None:
        return False, "Frame size is outside the supported range for the reference regions."
    h, w = frames[0].shape[:2]
    for (x, y, r, t) in regions.values():
        if not (0 <= x < r <= w and 0 <= y < t <= h):
            return False, f"Region {x},{y},{r},{t} is outside {w}x{h}"

    gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    rx, ry, rr, rt = regions["Reflection edge"]
    edge = gray[ry:rt, rx:rr]
    if float(edge.std()) < 5.0:
        return False, "Reflection edge region is too uniform; framing or lighting rejected"

    # The reflection edge should sit on water, not on foliage.
    # Foliage is strongly green-dominant; water reflects the sky (blue/cyan/white)
    # and is never strongly green-dominant in BGR.
    FOLIAGE_THRESHOLD = 20.0
    color = cv2.mean(frames[0][ry:rt, rx:rr])
    mean_b, mean_g, mean_r = color[:3]
    if mean_g > mean_b + FOLIAGE_THRESHOLD and mean_g > mean_r + FOLIAGE_THRESHOLD:
        return False, "Reflection edge color looks like foliage, not water; camera framing differs from reference"

    # The left and right reference regions should also avoid foliage.
    for side in ("Left of reflection", "Right of reflection"):
        sx, sy, sr, st = regions[side]
        side_color = cv2.mean(frames[0][sy:st, sx:sr])
        sb, sg, sr_ = side_color[:3]
        if sg > sb + FOLIAGE_THRESHOLD and sg > sr_ + FOLIAGE_THRESHOLD:
            return False, f"{side} looks like foliage; framing does not match the reference"

    return True, ""


def classify(live, reference, orientation_verified=True):
    """Provisional evidence rules; percentages are tuning candidates, not accuracy claims."""
    patches = [v for k, v in live.items() if k in BASE_REGIONS and v.get("usable")]
    if not patches:
        return {"direction": "none", "evidence_strength": "none", "status": "no_clear_directional_motion", "reason": "No textured patch exceeded its measured noise floor across separate windows."}
    votes = []
    for patch in patches:
        threshold = max(patch["noise_floor_normalized_px_per_second"], 0.05)
        dx = patch["median_dx_normalized_px_per_second"]
        windows = patch["window_medians"]
        persistent = sum(x < -threshold for x in windows) >= 2 or sum(x > threshold for x in windows) >= 2
        if abs(dx) <= threshold or not persistent:
            votes.append(("neutral", 0.0, abs(dx), threshold))
        elif patch["leftward_agreement"] >= patch["rightward_agreement"]:
            votes.append(("left", patch["leftward_agreement"], abs(dx), threshold))
        else:
            votes.append(("right", patch["rightward_agreement"], abs(dx), threshold))
    credible = [v for v in votes if v[0] != "neutral"]
    if not credible:
        return {"direction": "none", "evidence_strength": "none", "status": "no_clear_directional_motion", "reason": "Displacement remained below the measured noise floor or did not persist across windows."}
    left = [v for v in credible if v[0] == "left"]
    right = [v for v in credible if v[0] == "right"]
    if left and right:
        return {"direction": "mixed", "evidence_strength": "mixed", "status": "motion_detected_direction_mixed", "reason": "Credible patches disagreed or repeatedly reversed direction."}
    agreed = left or right
    likely = len(agreed) >= 2 and all(v[1] >= 0.80 and v[2] >= 2 * v[3] for v in agreed[:2])
    possible = (len(agreed) >= 2 and all(v[1] >= 0.60 for v in agreed[:2])) or (len(agreed) == 1 and agreed[0][1] >= 0.75)
    image_direction = agreed[0][0]
    geographic = "northward" if image_direction == "left" else "southward"
    direction = geographic if orientation_verified else image_direction
    if likely:
        return {"direction": direction, "evidence_strength": "likely", "status": f"likely_{direction}", "reason": "Strong noise-adjusted drift agreed across usable patches and separate time windows."}
    if possible:
        return {"direction": direction, "evidence_strength": "possible", "status": f"possible_{direction}", "reason": "Weak but credible noise-adjusted drift persisted without contradictory evidence."}
    return {"direction": "mixed", "evidence_strength": "mixed", "status": "motion_detected_direction_mixed", "reason": "Motion exceeded noise but directional agreement was insufficient."}


def annotate(frames, regions, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    f = frames[0].copy()
    for name, (x, y, r, t) in regions.items():
        cv2.rectangle(f, (x, y), (r, t), (0, 255, 255), 2)
        cv2.putText(f, name, (x, y - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    cv2.imwrite(str(output / "regions.jpg"), f)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True, help="Input video file (e.g., a Delray .ts segment)")
    p.add_argument(
        "--reference-json",
        type=Path,
        default=Path(__file__).parent / "fixtures" / "motion_reference" / "result.json",
        help="Recorded northward reference",
    )
    p.add_argument("--output", type=Path, default=Path("surface_flow_output"))
    p.add_argument("--observed-at", default=None, help="Verified ISO capture timestamp, if supplied by source")
    p.add_argument("--retrieved-at", required=True, help="ISO retrieval timestamp for this acquisition")
    p.add_argument("--acquisition-id", required=True, help="SHA-256 identity of this acquisition")
    p.add_argument("--source-url", default="", help="Source page URL to embed in report")
    p.add_argument("--minimum-duration", type=float, default=20.0, help="Minimum decoded seconds; lower only for explicit fixture tests")
    args = p.parse_args()

    try:
        reference = json.loads(args.reference_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Reference load failed: {exc}", file=sys.stderr)
        return 1

    try:
        frames, times, media = read_frames(args.input)
        h, w = frames[0].shape[:2] if frames else (0, 0)
        regions = scale_regions(h, w) if frames else None
        ok, reason = check_framing(frames, regions)
        if media["duration_seconds"] < args.minimum_duration:
            ok, reason = False, f"Only {media['duration_seconds']:.1f}s decoded; need at least {args.minimum_duration:g}s"
        if not ok:
            result = {
                "status": "unable_to_assess", "direction": "unknown", "evidence_strength": "unable",
                "freshness": "fresh", "reason": reason, "orientation_verified": False,
                "framing_verified": False, "regions": {}, "media": media,
                "analyzed_at": datetime.now(timezone.utc).isoformat(), "observed_at": args.observed_at,
                "retrieved_at": args.retrieved_at, "acquisition_id": args.acquisition_id,
                "user_label": "Surface flow: unable to assess",
                "automated_observation": reason,
                "interpretation": "Surface motion is experimental. Acquisition, decoding, framing, or camera checks prevented assessment. No current speed is reported.",
                "source_url": args.source_url,
            }
        else:
            live = analyze(frames, times, regions)
            classification = classify(live, reference, orientation_verified=True)
            label = f"{classification['evidence_strength']} {classification['direction']}" if classification['direction'] not in ("none", "mixed", "unknown") else classification['status'].replace('_', ' ')
            annotate(frames, regions, args.output)
            result = {
                **classification, "freshness": "fresh", "orientation_verified": True,
                "framing_verified": True, "regions": live, "media": media,
                "analyzed_at": datetime.now(timezone.utc).isoformat(), "observed_at": args.observed_at,
                "retrieved_at": args.retrieved_at, "acquisition_id": args.acquisition_id,
                "user_label": f"Surface flow: {label}", "automated_observation": classification["reason"],
                "interpretation": "Surface motion is an experimental, noise-adjusted optical-flow reading over separate clip windows, not a measured current or safety assessment.",
                "source_url": args.source_url,
            }
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        result = {
            "status": "unable_to_assess", "direction": "unknown", "evidence_strength": "unable",
            "freshness": "fresh", "reason": str(exc), "orientation_verified": False,
            "framing_verified": False, "regions": {}, "observed_at": args.observed_at,
            "retrieved_at": args.retrieved_at, "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "acquisition_id": args.acquisition_id, "user_label": "Surface flow: unable to assess",
            "automated_observation": str(exc),
            "interpretation": "Surface motion is experimental; input quality prevented assessment. No current speed is reported.",
            "source_url": args.source_url,
        }
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0


if __name__ == "__main__":
    sys.exit(main())
