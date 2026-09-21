"""Verify offline demo JSON and asset files are consistent."""
import json
import sys
from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parents[1] / "app" / "src" / "main" / "assets" / "demo"
JSON_FILE = ASSET_DIR / "recorded_replay.json"


def rewrite_url(url: str | None) -> Path | None:
    if not url or not url.startswith("file:///android_asset/demo/"):
        return None
    rel = url.replace("file:///android_asset/demo/", "")
    return ASSET_DIR / rel


def main() -> int:
    data = json.loads(JSON_FILE.read_text(encoding="utf-8"))
    assert data["mode"] == "recorded_replay", "expected recorded_replay mode"

    missing = []
    for cam in data.get("cameras", []):
        for key in ("image_url", "page_url", "source_url"):
            path = rewrite_url(cam.get(key))
            if path and not path.exists():
                missing.append((key, path))
    for a in data.get("water_appearance", []):
        for key in ("image_url", "source_url"):
            path = rewrite_url(a.get(key))
            if path and not path.exists():
                missing.append((key, path))
    motion = data.get("surface_motion")
    if motion:
        for key in ("regions_image_url", "clip_url"):
            path = rewrite_url(motion.get(key))
            if path and not path.exists():
                missing.append((key, path))
    algae = data.get("algae")
    if algae:
        for key in ("source_url", "source_image_url", "source_legend_url"):
            path = rewrite_url(algae.get(key))
            if path and not path.exists():
                missing.append((key, path))
        for region in algae.get("regions", []):
            path = rewrite_url(region.get("image_url"))
            if path and not path.exists():
                missing.append(("region_image_url", path))

    if missing:
        print("Missing referenced assets:")
        for key, path in missing:
            print(f"  {key}: {path}")
        return 1

    print("All referenced demo assets are present.")
    print(f"mode={data['mode']}, cameras={len(data['cameras'])}, "
          f"appearance={len(data['water_appearance'])}, "
          f"motion_status={data.get('surface_motion', {}).get('status')}, "
          f"algae_regions={len(data.get('algae', {}).get('regions', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
