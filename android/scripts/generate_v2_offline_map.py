import json
from pathlib import Path
import requests

BOUNDS = [-80.18, 25.65, -79.96, 27.20]
SOURCES = [
    ("shoreline", "https://gis.myfwc.com/hosting/rest/services/Open_Data/Florida_Shoreline_1to40000_Scale_Polygon/MapServer/3"),
    ("intracoastal", "https://gis.myfwc.com/hosting/rest/services/Open_Data/Intracoastal_Waterway_Florida/MapServer/8"),
]


def perpendicular_distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == 0 and dy == 0:
        return ((point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2) ** 0.5
    return abs(dy * point[0] - dx * point[1] + end[0] * start[1] - end[1] * start[0]) / (dx * dx + dy * dy) ** 0.5


def simplify(points, tolerance=0.00008):
    if len(points) <= 2:
        return points
    index, distance = max(enumerate(perpendicular_distance(point, points[0], points[-1]) for point in points[1:-1]), key=lambda item: item[1])
    index += 1
    if distance <= tolerance:
        return [points[0], points[-1]]
    return simplify(points[:index + 1], tolerance)[:-1] + simplify(points[index:], tolerance)


def simplify_geometry(geometry):
    geometry_type = geometry["type"]
    coordinates = geometry["coordinates"]
    if geometry_type == "Polygon":
        coordinates = [simplify(ring) for ring in coordinates]
    elif geometry_type == "MultiPolygon":
        coordinates = [[simplify(ring) for ring in polygon] for polygon in coordinates]
    elif geometry_type == "LineString":
        coordinates = simplify(coordinates)
    elif geometry_type == "MultiLineString":
        coordinates = [simplify(line) for line in coordinates]
    return {"type": geometry_type, "coordinates": coordinates}


def fetch(layer, url):
    params = {
        "where": "1=1",
        "geometry": ",".join(map(str, BOUNDS)),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "OBJECTID",
        "returnGeometry": "true",
        "f": "geojson",
    }
    response = requests.get(f"{url}/query", params=params, headers={"User-Agent": "PBC-Snorkel-V2-preview/1.0"}, timeout=180)
    response.raise_for_status()
    result = response.json()
    if "error" in result:
        raise RuntimeError(result["error"])
    for feature in result.get("features", []):
        feature["properties"] = {"layer": layer, "source": "Florida Fish and Wildlife Conservation Commission"}
        feature["geometry"] = simplify_geometry(feature["geometry"])
    return result.get("features", [])


features = [feature for layer, url in SOURCES for feature in fetch(layer, url)]
output = Path(__file__).parents[1] / "app/src/main/assets/map/southeast_florida.geojson"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({
    "type": "FeatureCollection",
    "name": "PBC Snorkel V2 offline map",
    "bbox": BOUNDS,
    "attribution": "Florida shoreline and Intracoastal Waterway · FWC Open Data",
    "source_urls": [url for _, url in SOURCES],
    "generated_for": "Visual preview; geometry is not navigational",
    "features": features,
}, separators=(",", ":")), encoding="utf-8")
print(f"Wrote {len(features)} features to {output} ({output.stat().st_size / 1024:.1f} KiB)")
