"""Import named OSM ways; never invent links between different ways.

Accepts locally downloaded OSM XML map extracts or an Overpass `out geom` JSON.
This is an offline maintenance command, not a runtime network dependency.
"""
import argparse
import json
import math
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"trunk", "primary", "secondary", "tertiary"}


def read_xml(directory):
    nodes, ways = {}, {}
    for path in sorted(directory.glob("*.osm")):
        data = ET.parse(path).getroot()
        nodes.update({n.attrib["id"]: [float(n.attrib["lat"]), float(n.attrib["lon"])]
                      for n in data.findall("node")})
        for way in data.findall("way"):
            tags = {t.attrib["k"]: t.attrib["v"] for t in way.findall("tag")}
            if tags.get("highway") in ALLOWED:
                ways[int(way.attrib["id"])] = (tags, [n.attrib["ref"] for n in way.findall("nd")])
    return [{"id": key, "tags": tags, "points": [nodes[n] for n in refs]}
            for key, (tags, refs) in sorted(ways.items())]


def clip_segment(a, b, bbox):
    """Liang–Barsky clipping preserves actual way edges at corridor boundaries."""
    south, west, north, east = bbox
    dy, dx = b[0] - a[0], b[1] - a[1]
    low, high = 0.0, 1.0
    for p, q in ((-dx, a[1] - west), (dx, east - a[1]),
                 (-dy, a[0] - south), (dy, north - a[0])):
        if p == 0:
            if q < 0:
                return None
            continue
        value = q / p
        if p < 0:
            low = max(low, value)
        else:
            high = min(high, value)
        if low > high:
            return None
    points = [[round(a[0] + t * dy, 7), round(a[1] + t * dx, 7)] for t in (low, high)]
    return points if points[0] != points[1] else None


def clipped_paths(points, bbox):
    paths, current = [], []
    for a, b in zip(points, points[1:]):
        segment = clip_segment(a, b, bbox)
        if segment is None:
            if current:
                paths.append(current)
                current = []
        elif current and current[-1] == segment[0]:
            current.append(segment[1])
        else:
            if current:
                paths.append(current)
            current = segment
    if current:
        paths.append(current)
    return paths


def distance(a, b):
    return math.hypot((b[1] - a[1]) * math.cos(math.radians(a[0])), b[0] - a[0])


def path_length(path):
    return sum(distance(a, b) for a, b in zip(path, path[1:]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--osm-dir", type=Path)
    source.add_argument("--overpass-json", type=Path)
    parser.add_argument("--retrieved-at", help="Source download time; snapshot metadata is used by default")
    args = parser.parse_args()
    if args.osm_dir:
        ways = read_xml(args.osm_dir)
        retrieved_at = args.retrieved_at or datetime.now(UTC).isoformat()
    else:
        snapshot = json.loads(args.overpass_json.read_text(encoding="utf-8"))
        elements = snapshot["elements"]
        retrieved_at = args.retrieved_at or snapshot.get("retrieved_at") or datetime.now(UTC).isoformat()
        ways = [{"id": w["id"], "tags": w["tags"],
                 "points": [[n["lat"], n["lon"]] for n in w["geometry"]]}
                for w in elements if w.get("tags", {}).get("highway") in ALLOWED]
    catalog_path = ROOT / "packages/data/dhaka-main-roads.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    selections = json.loads((ROOT / "packages/data/dhaka-road-geometry-selection.json").read_text(encoding="utf-8"))
    for road in catalog:
        selection = selections[road["id"]]
        names = {n.casefold() for n in selection["names"]}
        paths, ids = [], []
        for way in sorted(ways, key=lambda w: w["id"]):
            tags = way["tags"]
            if not any(tags.get(key, "").casefold() in names for key in ("name", "name:en")):
                continue
            parts = clipped_paths(way["points"], selection["bbox"])
            if parts:
                paths.extend(parts)
                ids.append(way["id"])
        if not paths:
            raise ValueError(f"No OSM geometry for {road['id']}; catalog was not written")
        longest = max(paths, key=path_length)
        road.update(paths=paths, path=longest, center=longest[len(longest) // 2],
                    geometry_source="openstreetmap", osm_way_ids=ids,
                    geometry_retrieved_at=retrieved_at)
        for key in ("from", "to"):
            if key in selection:
                road[key] = selection[key]
        print(f"{road['id']}: {len(ids)} ways, {sum(map(len, paths))} vertices")
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
