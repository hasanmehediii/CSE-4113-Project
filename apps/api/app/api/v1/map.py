import json
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException, Query
from pydantic import AwareDatetime
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.dependencies import Database
from app.models.civic import Area, Category, Complaint, Road, now
from app.services.civic_service import OPEN
from app.services.road_catalog import MAIN_ROADS

router = APIRouter(tags=["Public map"])


@router.get("/categories")
def categories(db: Database):
    return [
        {"code": r.code, "label": r.label, "base_priority": r.base_priority}
        for r in db.scalars(select(Category).order_by(Category.label))
    ]


@router.get("/areas")
def areas(db: Database):
    return [
        {"id": r.id, "name": r.name, "ward": r.ward}
        for r in db.scalars(select(Area).order_by(Area.name))
    ]


@router.get("/map/roads")
def roads(
    db: Database,
    area_id: str | None = None,
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    main_only: bool = False,
):
    query = select(Road)
    if main_only:
        query = query.where(Road.id.in_(MAIN_ROADS))
    if area_id:
        query = query.where(Road.area_id == area_id)
    catalog = db.scalars(query.order_by(Road.name).offset(offset).limit(limit)).all()
    ids = [r.id for r in catalog]
    # Restrict observations to selected roads. Reports never expose account contact/NID data.
    reports = (
        db.scalars(
            select(Complaint)
            .where(Complaint.road_id.in_(ids), Complaint.status != "false")
            .order_by(Complaint.created_at.desc(), Complaint.id)
        ).all()
        if ids
        else []
    )
    grouped = {}
    for report in reports:
        grouped.setdefault(report.road_id, []).append(report)
    results = []
    for road in catalog:
        geometry = MAIN_ROADS.get(road.id, {})
        latitude, longitude = geometry.get("center", [road.latitude, road.longitude])
        rows = grouped.get(road.id, [])
        active = [r for r in rows if r.kind == "complaint" and r.status in OPEN]
        recent_updates = [
            r for r in rows if r.kind == "road_update" and r.created_at >= now() - 86400
        ]
        confirmed = [r for r in rows if r.status == "resolved" and r.updated_at >= now() - 86400]
        latest = max(recent_updates + confirmed, key=lambda r: r.updated_at, default=None)
        condition = (
            "bad"
            if active
            else (
                "good"
                if latest and latest.status == "resolved"
                else latest.condition
                if latest
                else "unknown"
            )
        )
        historical = len(
            [r for r in rows if r.kind == "complaint" and r.created_at >= now() - 90 * 86400]
        )
        results.append(
            {
                "id": road.id,
                "name": road.name,
                "area_id": road.area_id,
                "latitude": latitude,
                "longitude": longitude,
                "condition": condition,
                "open_complaints": len(active),
                "last_report_at": rows[0].created_at if rows else None,
                "historical_reports_90d": historical,
                "sensitivity": "high" if historical >= 3 else "insufficient_data",
                "sensitivity_source": "historical_report_count",
                "prediction": None,
                "path": geometry.get("path"),
                "paths": geometry.get("paths"),
                "segment_from": geometry.get("from"),
                "segment_to": geometry.get("to"),
                "geometry_source": geometry.get("geometry_source"),
                "geometry_attribution": "© OpenStreetMap contributors" if geometry.get("osm_way_ids") else None,
            }
        )
    return results


@router.get("/map/predictions")
def predictions(
    at: AwareDatetime,
    rainfall_mm: float = Query(default=0, ge=0, le=150, allow_inf_nan=False),
    forecast_horizon_min: int = Query(default=60, ge=30, le=120),
):
    """Public scenario inference; the browser never calls the internal ML service."""
    if forecast_horizon_min not in (30, 60, 120):
        raise HTTPException(422, "Forecast horizon must be 30, 60 or 120 minutes")
    if abs(at.timestamp() - datetime.now(UTC).timestamp()) > 7 * 86400:
        raise HTTPException(422, "Choose a time within seven days of now")
    payload = json.dumps({"at": at.isoformat(), "rainfall_mm": rainfall_mm,
                          "forecast_horizon_min": forecast_horizon_min}).encode()
    request = Request(
        get_settings().ml_service_url.rstrip("/") + "/road-risk/predict",
        data=payload, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError):
        raise HTTPException(503, "Road prediction unavailable. Train the road-risk model and start the ML service.") from None


@router.get("/map/hotspots")
def hotspots(db: Database):
    # Deterministic ~300m grid clusters are a transparent baseline before ML clustering.
    lat_cell = func.floor(Complaint.latitude / 0.003)
    lon_cell = func.floor(Complaint.longitude / 0.003)
    rows = db.execute(
        select(
            lat_cell,
            lon_cell,
            func.count(),
            func.avg(Complaint.latitude),
            func.avg(Complaint.longitude),
        )
        .where(Complaint.kind == "complaint", Complaint.status.in_(OPEN))
        .group_by(lat_cell, lon_cell)
        .order_by(func.count().desc())
        .limit(100)
    ).all()
    return [
        {
            "cell": f"{int(a)}:{int(b)}",
            "count": n,
            "latitude": lat,
            "longitude": lon,
            "method": "grid_0.003_degrees",
        }
        for a, b, n, lat, lon in rows
    ]
