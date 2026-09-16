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


def read_frames(path, step=6):
    c = cv2.VideoCapture(str(path))
    frames = []
    while True:
        ok, f = c.read()
        if not ok:
            break
        if int(c.get(cv2.CAP_PROP_POS_FRAMES)) % step == 1:
            frames.append(f)
    c.release()
    return frames


def analyze(frames, regions):
    rows = {k: [] for k in regions}
    for a, b in zip(frames, frames[1:]):
        for name, (x, y, r, t) in regions.items():
            aa = cv2.cvtColor(a[y:t, x:r], cv2.COLOR_BGR2GRAY)
            bb = cv2.cvtColor(b[y:t, x:r], cv2.COLOR_BGR2GRAY)
            if aa.shape != bb.shape:
                raise ValueError("Frame crop size mismatch")
            flow = cv2.calcOpticalFlowFarneback(aa, bb, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            rows[name].append([float(np.median(flow[:, :, 0])), float(np.median(flow[:, :, 1]))])
    result = {}
    for name, vals in rows.items():
        arr = np.array(vals)
        result[name] = {
            "median_dx_pixels_per_0_2s": round(float(np.median(arr[:, 0])), 3),
            "median_dy_pixels_per_0_2s": round(float(np.median(arr[:, 1])), 3),
            "leftward_pair_percent": round(float((arr[:, 0] < 0).mean() * 100), 1),
            "pair_count": len(vals),
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
    return True, ""


def classify(live, reference, agreement_threshold=0.65):
    names = list(BASE_REGIONS.keys())
    dxs = [live[n]["median_dx_pixels_per_0_2s"] for n in names]
    dys = [live[n]["median_dy_pixels_per_0_2s"] for n in names]
    lefts = [live[n]["leftward_pair_percent"] / 100.0 for n in names]
    pair_counts = [live[n]["pair_count"] for n in names]

    if any(c < 10 for c in pair_counts):
        return "unclear", "Too few frame pairs for a reliable motion estimate."

    # Calibrate thresholds from the recorded northward reference.
    ref_right = reference.get("Right of reflection", {})
    ref_edge = reference.get("Reflection edge", {})
    ref_mag = max(
        0.05,
        abs(ref_right.get("median_dx_pixels_per_0_2s", 0.0)),
        abs(ref_edge.get("median_dx_pixels_per_0_2s", 0.0)),
    )
    motion_threshold = 0.1 * ref_mag
    camera_move_threshold = ref_mag

    # Camera-movement check: all regions moving together too strongly suggests pan.
    dx_range = max(dxs) - min(dxs)
    if abs(dx_range) < 0.1 and abs(np.median(dxs)) > camera_move_threshold:
        return "unclear", "Similar large horizontal motion across all regions suggests camera movement, not surface flow."

    edge_left = live["Reflection edge"]["leftward_pair_percent"]
    right_left = live["Right of reflection"]["leftward_pair_percent"]
    edge_mag = abs(live["Reflection edge"]["median_dx_pixels_per_0_2s"])
    right_mag = abs(live["Right of reflection"]["median_dx_pixels_per_0_2s"])

    if edge_mag < motion_threshold and right_mag < motion_threshold:
        return "unclear", "Horizontal motion is too weak to classify."

    if edge_left < (1 - agreement_threshold) * 100 and right_left < (1 - agreement_threshold) * 100:
        return "likely_southward", "Surface motion appears toward the right in the frame, consistent with southward flow given the reference orientation."

    if edge_left > agreement_threshold * 100 and right_left > agreement_threshold * 100:
        return "likely_northward", "Surface motion appears toward the left in the frame, consistent with the recorded northward reference."

    return "unclear", "Motion pattern does not clearly match the northward or southward reference."


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
    p.add_argument("--observed-at", default=None, help="ISO observed timestamp (default now)")
    p.add_argument("--source-url", default="", help="Source page URL to embed in report")
    args = p.parse_args()

    try:
        reference = json.loads(args.reference_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Reference load failed: {exc}", file=sys.stderr)
        return 1

    observed_at = args.observed_at or datetime.now(timezone.utc).isoformat()
    try:
        frames = read_frames(args.input)
        h, w = frames[0].shape[:2] if frames else (0, 0)
        regions = scale_regions(h, w) if frames else None
        ok, reason = check_framing(frames, regions)
        if not ok:
            result = {
                "status": "unclear",
                "framing_verified": False,
                "framing_reject_reason": reason,
                "regions": {},
                "classified_at_utc": datetime.now(timezone.utc).isoformat(),
                "observed_at": observed_at,
                "user_label": "Surface flow: unclear",
                "automated_observation": "Could not verify Delray framing or lighting.",
                "interpretation": "Surface motion is experimental. Camera framing, lighting or stream quality prevented a direction estimate. No current speed is reported.",
                "source_url": args.source_url,
            }
        else:
            live = analyze(frames, regions)
            status, note = classify(live, reference)
            user_label = f"Surface flow: {status.replace('_', ' ')}"
            annotate(frames, regions, args.output)
            result = {
                "status": status,
                "framing_verified": True,
                "regions": live,
                "classified_at_utc": datetime.now(timezone.utc).isoformat(),
                "observed_at": observed_at,
                "user_label": user_label,
                "automated_observation": note,
                "interpretation": "Surface motion is an experimental optical-flow reading from a short camera clip, not a measured current. Results assume the camera is fixed and oriented like the recorded northward reference. Weak or inconsistent motion is reported as unclear.",
                "source_url": args.source_url,
            }
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"Surface flow POC failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
