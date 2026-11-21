"""Audit how packages/new-data segments map onto the map's main-road corridors.

Run from apps/ml-service:

    uv run python -m app.audit_road_mapping          # readable report
    uv run python -m app.audit_road_mapping --json   # machine-readable

Structural errors (unknown, shared or one-direction segments, corridors without a
mapping) exit with status 1. Endpoint and length findings are review notes, not
proof of an error: the supplied junctions have no coordinates, so a mapping can
only be checked against names and the drawn OpenStreetMap corridor.
"""
import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from itertools import pairwise
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SEGMENTS = REPO_ROOT / "packages/new-data/dhaka_directed_road_segments_bilingual.csv"
MAPPING = REPO_ROOT / "packages/data/dhaka-road-segment-mapping.json"
CATALOG = REPO_ROOT / "packages/data/dhaka-main-roads.json"
# Road length divided by straight-line distance is usually 1.3-2.0 for these corridors.
LENGTH_RATIO_REVIEW = 2.2


def load(segments=SEGMENTS, mapping=MAPPING, catalog=CATALOG):
    with segments.open(encoding="utf-8-sig", newline="") as source:
        rows = {row["segment_id"]: row for row in csv.DictReader(source)}
    return (rows, json.loads(mapping.read_text("utf-8"))["roads"],
            json.loads(catalog.read_text("utf-8")))


def _key(name: str) -> str:
    return re.sub(r"[^0-9a-z]", "", name.casefold())


def same_place(a: str, b: str) -> bool:
    """Tolerate spelling/suffix variants such as Shahbag/Shahbagh or Kuril/Kuril Bishwa Road."""
    a, b = _key(a), _key(b)
    return bool(a and b) and (a in b or b in a)


def _km(a, b) -> float:
    cos_lat = math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((a[0] - b[0]) * 111.32, (a[1] - b[1]) * 111.32 * cos_lat)


def corridor_span_km(road: dict) -> float:
    points = [p for path in (road.get("paths") or [road["path"]]) for p in path]
    first = max(points, key=lambda p: _km(p, points[0]))
    return max(_km(first, p) for p in points)


def audit(segments: dict, mapping: dict, catalog: list) -> dict:
    roads = {road["id"]: road for road in catalog}
    mapped = [s for ids in mapping.values() for s in ids]
    errors = []
    for road_id in sorted(set(roads) - set(mapping)):
        errors.append(f"{road_id}: catalog road has no mapped segments")
    for road_id in sorted(set(mapping) - set(roads)):
        errors.append(f"{road_id}: mapped road is not in the map catalog")
    for segment, count in sorted(Counter(mapped).items()):
        if segment not in segments:
            errors.append(f"{segment}: unknown segment ID")
        if count > 1:
            errors.append(f"{segment}: mapped {count} times")
    corridors = []
    for road_id, ids in mapping.items():
        if road_id not in roads:
            continue
        road = roads[road_id]
        for base, count in sorted(Counter(s[:-1] for s in ids).items()):
            if count != 2:
                errors.append(f"{road_id}: {base} is mapped in one direction only")
        if not ids:
            errors.append(f"{road_id}: empty mapping")
            continue
        chain = [segments[s] for s in ids if s in segments and s.endswith("A")]
        notes = []
        for current, following in pairwise(chain):
            if not same_place(current["to_name_en"], following["from_name_en"]):
                notes.append(f"chain breaks between {current['segment_id']} and {following['segment_id']}")
        start, end = (chain[0]["from_name_en"], chain[-1]["to_name_en"]) if chain else ("", "")
        wanted = (road.get("from", ""), road.get("to", ""))
        forward = same_place(start, wanted[0]) and same_place(end, wanted[1])
        backward = same_place(start, wanted[1]) and same_place(end, wanted[0])
        if chain and not (forward or backward):
            notes.append(f"endpoints differ: corridor {wanted[0]} -> {wanted[1]}, "
                         f"mapped chain {start} -> {end}")
        length = sum(float(row["estimated_length_km"]) for row in chain)
        span = corridor_span_km(road)
        ratio = length / span if span else math.inf
        if ratio > LENGTH_RATIO_REVIEW:
            notes.append(f"mapped length {length:.1f} km is {ratio:.1f}x the drawn corridor's "
                         f"{span:.2f} km end-to-end distance")
        corridors.append({
            "road_id": road_id, "name": road["name"], "corridor": list(wanted),
            "segments": len(ids), "chain": [start, end], "mapped_km": round(length, 2),
            "drawn_span_km": round(span, 2), "ratio": round(ratio, 2), "review": notes,
        })
    unmapped = sorted(set(segments) - set(mapped))
    return {
        "dataset_segments": len(segments), "mapped_segments": len(set(mapped)),
        "unmapped_segments": len(unmapped), "map_corridors": len(roads),
        "mapped_corridors": len(set(mapping) & set(roads)),
        "unmapped_by_dataset_road": dict(sorted(Counter(
            segments[s]["corridor_name_en"] for s in unmapped).items())),
        "errors": errors, "corridors": corridors,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    report = audit(*load())
    if parser.parse_args(argv).json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if report["errors"] else 0
    print(f"Dataset segments: {report['dataset_segments']} | mapped: {report['mapped_segments']} "
          f"| unmapped: {report['unmapped_segments']}")
    print(f"Map corridors: {report['map_corridors']} | with a mapping: {report['mapped_corridors']}")
    print("Structural errors: " + ("none" if not report["errors"] else ""))
    for error in report["errors"]:
        print(f"  - {error}")
    for row in report["corridors"]:
        status = "REVIEW" if row["review"] else "ok"
        print(f"{status:6} {row['road_id']:22} {row['segments']:2} segments  "
              f"{row['mapped_km']:5.1f} km mapped / {row['drawn_span_km']:4.2f} km drawn span")
        for note in row["review"]:
            print(f"         - {note}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
