"""Stable Dhaka corridor IDs with checked-in OpenStreetMap road geometry."""
import json
from pathlib import Path

from sqlalchemy import select

from app.models.civic import Area, Road

CATALOG_PATH = Path(__file__).resolve().parents[4] / "packages/data/dhaka-main-roads.json"
MAIN_ROADS = {row["id"]: row for row in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))}


def seed_main_roads(db):
    for row in MAIN_ROADS.values():
        area = db.scalar(select(Area).where(Area.name == row["area"]))
        if area is None:
            area = Area(name=row["area"])
            db.add(area)
            db.flush()
        lat, lon = row.get("center", row["path"][len(row["path"]) // 2])
        road = db.get(Road, row["id"])
        if road is None:
            db.add(Road(id=row["id"], name=row["name"], area_id=area.id,
                        latitude=lat, longitude=lon))
        else:
            # Repair old approximate catalog centers without changing report IDs.
            road.latitude, road.longitude = lat, lon
    db.flush()
