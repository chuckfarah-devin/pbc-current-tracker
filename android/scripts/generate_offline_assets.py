"""Generate android/app/src/main/assets/demo/recorded_replay.json from the backend."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

# Make app importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from fastapi.testclient import TestClient
from app.main import app

HANDOFF_DEMO = Path(
    os.environ.get("PBC_HANDOFF_DIR", r"C:\Users\chuck\PBC Snorkel conditions\PBC-Snorkel-Devin-Handoff\devin-handoff")
) / "demo"
# script lives in android/scripts/; project-relative path is android/app/src/main/assets/demo.
ASSET_DIR = Path(__file__).resolve().parents[1] / "app" / "src" / "main" / "assets" / "demo"

def main() -> None:
    client = TestClient(app)
    r = client.get("/api/snorkel-conditions")
    r.raise_for_status()
    data = r.json()

    # Rewrite image URLs so they point into local assets.
    def rewrite_url(url: str | None) -> str | None:
        if not url:
            return url
        # backend serves these under /fixtures/ from the demo directory.
        m = re.match(r"http://[^/]+/fixtures/(.+)", url)
        if m:
            return f"file:///android_asset/demo/{m.group(1)}"
        return url

    for cam in data.get("cameras", []):
        # Camera health images are large and are not displayed in the MVP UI
        # (the hero and evidence use appearance images). Keep the JSON metadata
        # but drop local image references to keep the APK small.
        cam["image_url"] = None
        cam["page_url"] = rewrite_url(cam.get("page_url"))
        cam["source_url"] = rewrite_url(cam.get("source_url"))

    for a in data.get("water_appearance", []):
        a["image_url"] = rewrite_url(a.get("image_url"))
        a["source_url"] = rewrite_url(a.get("source_url"))

    algae = data.get("algae")
    if algae:
        algae["source_url"] = rewrite_url(algae.get("source_url"))
        algae["source_image_url"] = rewrite_url(algae.get("source_image_url"))
        algae["source_legend_url"] = rewrite_url(algae.get("source_legend_url"))
        for region in algae.get("regions", []):
            region["image_url"] = rewrite_url(region.get("image_url"))

    motion = data.get("surface_motion")
    if motion:
        motion["regions_image_url"] = rewrite_url(motion.get("regions_image_url"))
        motion["clip_url"] = rewrite_url(motion.get("clip_url"))

    # Copy only the fixtures actually used by the offline demo UI.
    # Camera health PNGs are large and not displayed; keep only the JSONs and the
    # small images referenced by the appearance / surface-flow / sargassum cards.
    required_files = [
        "appearance/result.json",
        "appearance/delray.jpg",
        "appearance/lake_worth_s16.jpg",
        "camera/result.json",
        "camera/delray.png",
        "motion/result.json",
        "motion/regions.jpg",
        "sargassum/result.json",
        "sargassum/boynton_delray.png",
        "sargassum/palm_beach_to_miami.png",
        "weather/result.json",
    ]
    if ASSET_DIR.exists():
        shutil.rmtree(ASSET_DIR)
    for rel_path in required_files:
        src = HANDOFF_DEMO / rel_path
        if not src.exists():
            print(f"Warning: missing demo fixture {src}", file=sys.stderr)
            continue
        dst = ASSET_DIR / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # Save the rewritten response.
    recorded_replay = ASSET_DIR / "recorded_replay.json"
    recorded_replay.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Print size summary.
    total = sum(f.stat().st_size for f in ASSET_DIR.rglob("*") if f.is_file())
    print(f"Wrote {ASSET_DIR}")
    print(f"Total asset size: {total / 1024:.1f} KB")
    print(f"Files: {len(list(ASSET_DIR.rglob('*')))}")


if __name__ == "__main__":
    main()
