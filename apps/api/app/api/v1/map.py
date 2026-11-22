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
from app.services.civic_service import OPEN, incident_counts_on_map, report_counts_on_map
from app.services.road_catalog import MAIN_ROADS
from app.services.road_status import road_status

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
    last_reports = dict(db.execute(
        select(Complaint.road_id, func.max(Complaint.created_at))
        .where(Complaint.road_id.in_(ids), Complaint.status != "false", report_counts_on_map())
        .group_by(Complaint.road_id)
    ).all()) if ids else {}
    # Restrict observations to selected roads. Reports never expose account contact/NID data.
    reports = (
        db.scalars(
            select(Complaint)
            .where(Complaint.road_id.in_(ids), Complaint.status != "false", Complaint.incident_id.is_(None),
                   incident_counts_on_map())
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
                "last_report_at": last_reports.get(road.id),
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


@router.get("/map/road-status")
def map_road_status(db: Database, at: AwareDatetime | None = None):
    """Traffic and waterlogging per main road from community reports (last 4 hours),
    the synthetic historical profile for `at` (default now), and Open-Meteo rainfall."""
    if at and abs(at.timestamp() - datetime.now(UTC).timestamp()) > 366 * 86400:
        raise HTTPException(422, "Choose a time within a year of now")
    return road_status(db, at)


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
            result = json.load(response)
    except HTTPError as error:
        raise HTTPException(*ml_failure(error)) from None
    except (URLError, TimeoutError, OSError):
        raise HTTPException(
            503, "Road prediction service is not reachable. Start the ML service, then try again."
        ) from None
    except ValueError:
        raise HTTPException(502, INVALID_PREDICTION) from None
    if not valid_forecast(result, forecast_horizon_min):
        raise HTTPException(502, INVALID_PREDICTION)
    return result


INVALID_PREDICTION = "The ML service returned an invalid prediction response. Try again."


def _probability(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and 0 <= value <= 1


def valid_forecast(result, horizon: int) -> bool:
    """The map renders `at` and every road's probabilities, so require them before answering 200."""
    if not isinstance(result, dict) or not isinstance(result.get("roads"), list):
        return False
    try:
        if datetime.fromisoformat(result["at"]).tzinfo is None:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    # A response for another horizon would be shown against the wrong scenario.
    if result.get("forecast_horizon_min", horizon) != horizon:
        return False
    return all(
        isinstance(road, dict) and isinstance(road.get("road_id"), str)
        and _probability(road.get("waterlogging_probability"))
        and _probability(road.get("traffic_probability"))
        for road in result["roads"]
    )


def ml_failure(error: HTTPError) -> tuple[int, str]:
    """Keep the ML service's own reason (missing/incompatible model) visible to the map."""
    try:
        detail = json.load(error).get("detail")
    except (ValueError, AttributeError, OSError):
        detail = None
    if error.code == 503:
        reason = detail if isinstance(detail, str) and detail else "The road-risk model is not loaded."
        return 503, f"Road prediction unavailable. {reason[:400]}"
    if error.code == 422 and isinstance(detail, str) and detail:
        # A scenario the loaded model cannot serve, e.g. a legacy model and a 30-minute horizon.
        return 422, detail[:400]
    return 502, f"The ML service could not complete this prediction (HTTP {error.code}). Try again."


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
        .where(Complaint.kind == "complaint", Complaint.status.in_(OPEN), Complaint.incident_id.is_(None))
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
