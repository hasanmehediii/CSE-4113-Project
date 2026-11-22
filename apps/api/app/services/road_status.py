"""Traffic and waterlogging status for the map's main roads from three separate sources.

- community: citizens' reports on the road in the last 4 hours (observations);
- historical: a synthetic hourly profile (packages/data/dhaka-road-history.json, made by
  scripts/generate-road-history.py) for the season, day type and hour;
- weather (shown as "Now"): current rainfall from the open-source Open-Meteo API picks the
  matching part of the history (this hour, this much rain) to predict each road now; with
  community reports it drives the "avoid now" list. Open-Meteo has no traffic data, and no
  open live traffic feed covers Dhaka.

Each source is reported separately and never presented as another; a weather failure
does not hide the other two.
"""
import json
import threading
import time
from datetime import UTC, datetime, timedelta, timezone
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select

from app.models.civic import Complaint
from app.services.road_catalog import CATALOG_PATH, MAIN_ROADS

DHAKA = timezone(timedelta(hours=6), name="Asia/Dhaka")
COMMUNITY_WINDOW_SECONDS = 4 * 3600
HISTORY = json.loads((CATALOG_PATH.parent / "dhaka-road-history.json").read_text("utf-8"))
HAZARDS = ("traffic", "waterlogging")
WATER_CATEGORIES = {"road_flooding", "waterlogging_recurring"}
TRAFFIC_CATEGORIES = {"traffic_jam"}
# Older road-form traffic reports used the "other" category with this title marker.
LEGACY_TRAFFIC_TITLE = "Traffic / obstruction"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TTL_SECONDS = 600
WEATHER_STALE_SECONDS = 3600
# Probability bands for the synthetic profile; waterlogging is rarer, so its bands are lower.
BANDS = {"traffic": (0.6, 0.3), "waterlogging": (0.25, 0.1)}


def hazard_of(report: Complaint) -> str | None:
    if report.category_code in WATER_CATEGORIES:
        return "waterlogging"
    if report.category_code in TRAFFIC_CATEGORIES or (
        report.category_code == "other" and LEGACY_TRAFFIC_TITLE in report.title
    ):
        return "traffic"
    return None


def _blank_community():
    return {"status": "none", "reports": 0, "clear_reports": 0, "last_report_at": None, "expires_at": None}


def community_status(db, now: int) -> dict[str, dict]:
    """Reports from the last 4 hours. The latest report per road and hazard decides:
    a problem report means "reported" (until 4 hours after it); a clear update means "clear"."""
    rows = db.scalars(
        select(Complaint).where(
            Complaint.road_id.in_(list(MAIN_ROADS)),
            Complaint.created_at >= now - COMMUNITY_WINDOW_SECONDS,
            Complaint.status.notin_(("false", "resolved")),
        ).order_by(Complaint.created_at, Complaint.id)
    ).all()
    result = {road_id: {hazard: _blank_community() for hazard in HAZARDS} for road_id in MAIN_ROADS}
    for report in rows:
        hazard = hazard_of(report)
        if hazard is None:
            continue
        entry = result[report.road_id][hazard]
        clear = report.kind == "road_update" and report.condition == "good"
        if report.kind == "road_update" and report.condition not in ("good", "bad"):
            continue
        if clear:
            entry["clear_reports"] += 1
            entry["status"] = "clear"
            entry["expires_at"] = None
        else:
            entry["reports"] += 1
            entry["status"] = "reported"
            entry["expires_at"] = report.created_at + COMMUNITY_WINDOW_SECONDS
        entry["last_report_at"] = report.created_at
    return result


def season_of(month: int) -> str:
    return next(name for name, months in HISTORY["seasons"].items() if month in months)


def day_type_of(weekday: int) -> str:
    return {4: "friday", 5: "saturday"}.get(weekday, "workday")


def level_for(hazard: str, value: float) -> str:
    high, moderate = BANDS[hazard]
    return "high" if value >= high else "moderate" if value >= moderate else "low"


def rain_band(rain_3h: float) -> str:
    """Same bands as scripts/generate-road-history.py."""
    return "none" if rain_3h < 0.5 else "light" if rain_3h < 8 else "heavy"


def profile_status(at: datetime, band: str) -> tuple[dict, dict[str, dict]]:
    """Probability and level per road from the synthetic history for `at` and a rain band."""
    local = at.astimezone(DHAKA)
    season, day_type = season_of(local.month), day_type_of(local.weekday())
    period = {"season": season, "day_type": day_type, "hour": local.hour}
    result = {}
    for road_id in MAIN_ROADS:
        profile = HISTORY["roads"].get(road_id)
        result[road_id] = {
            hazard: ({"probability": (value := profile[hazard][season][day_type][band][local.hour]),
                      "level": level_for(hazard, value)} if profile else {"probability": None, "level": "unknown"})
            for hazard in HAZARDS
        }
    return period, result


def historical_status(at: datetime) -> tuple[dict, dict[str, dict]]:
    """What usually happens at this time in any weather."""
    return profile_status(at, "any")


_weather_lock = threading.Lock()
_weather_cache: dict = {}


DHAKA_CENTRE = (23.8103, 90.4125)


def _rain(location: dict) -> tuple[float, float, str]:
    current_time = location["current"]["time"]
    hourly = [value or 0.0 for time_, value in zip(location["hourly"]["time"], location["hourly"]["precipitation"],
                                                     strict=True) if time_ <= current_time]
    return float(sum(hourly[-1:])), float(sum(hourly[-3:])), current_time


def _fetch_open_meteo() -> dict:
    """One Open-Meteo request: each road centre plus the city centre for a "Dhaka now" summary."""
    road_ids = list(MAIN_ROADS)
    points = [MAIN_ROADS[road_id]["center"] for road_id in road_ids] + [DHAKA_CENTRE]
    query = urlencode({
        "latitude": ",".join(f"{lat:.4f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.4f}" for _, lon in points),
        "hourly": "precipitation", "past_hours": 6, "forecast_hours": 1,
        "current": "precipitation,temperature_2m,weather_code", "timezone": "Asia/Dhaka",
    })
    request = Request(f"{OPEN_METEO_URL}?{query}", headers={"User-Agent": "DubsiBhai road status"})
    with urlopen(request, timeout=10) as response:
        data = json.load(response)
    locations = data if isinstance(data, list) else [data]
    if len(locations) != len(points):
        raise ValueError("Open-Meteo returned an unexpected number of locations")
    roads = {}
    for road_id, location in zip(road_ids, locations, strict=False):
        rain_1h, rain_3h, observed = _rain(location)
        roads[road_id] = {"rain_mm_1h": round(rain_1h, 1), "rain_mm_3h": round(rain_3h, 1), "observed_at": observed}
    centre = locations[-1]
    rain_1h, rain_3h, observed = _rain(centre)
    city = {"temperature_c": centre["current"].get("temperature_2m"),
            "weather_code": centre["current"].get("weather_code"),
            "rain_mm_1h": round(rain_1h, 1), "rain_mm_3h": round(rain_3h, 1), "observed_at": observed}
    return {"roads": roads, "city": city}


def clear_weather_cache():
    with _weather_lock:
        _weather_cache.clear()


def weather_status(fetch=None, clock=time.time) -> dict:
    """Cached for 10 minutes; a failed refresh serves the last result for up to an hour."""
    fetch = fetch or _fetch_open_meteo
    with _weather_lock:
        cached = _weather_cache.get("value")
        age = clock() - _weather_cache.get("at", 0)
        if cached and age < WEATHER_TTL_SECONDS:
            return {**cached, "status": "live"}
        try:
            fetched = fetch()
        except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
            if cached and age < WEATHER_STALE_SECONDS:
                return {**cached, "status": "stale"}
            return {"status": "unavailable", "fetched_at": None, "roads": {}, "city": None,
                    "message": "Live rainfall from Open-Meteo is not available right now."}
        value = {"fetched_at": datetime.now(UTC).isoformat(), "roads": fetched["roads"], "city": fetched.get("city")}
        _weather_cache.update(value=value, at=clock())
        return {**value, "status": "live"}


def predicted_now(live: dict, now: datetime) -> dict[str, dict | None]:
    """Combine current Open-Meteo rain with the history for this hour and that much rain."""
    result = {}
    for road_id in MAIN_ROADS:
        weather = live["roads"].get(road_id)
        if not weather:
            result[road_id] = None
            continue
        band = rain_band(weather["rain_mm_3h"])
        _, profile = profile_status(now, band)
        result[road_id] = {**weather, "rain_band": band, **profile[road_id]}
    return result


def avoid_now(community: dict, predicted: dict) -> list[dict]:
    """Roads to avoid: reported problems first (actual conditions), then high predicted risk."""
    avoid = []
    for road_id in MAIN_ROADS:
        reasons = [f"reported_{hazard}" for hazard in HAZARDS if community[road_id][hazard]["status"] == "reported"]
        now = predicted.get(road_id)
        reasons += [f"likely_{hazard}" for hazard in HAZARDS if now and now[hazard]["level"] == "high"]
        if reasons:
            avoid.append({"road_id": road_id, "reasons": reasons})
    return sorted(avoid, key=lambda row: (not any(r.startswith("reported") for r in row["reasons"]),
                                          -len(row["reasons"])))


def road_status(db, at: datetime | None = None) -> dict:
    now = int(time.time())
    current = datetime.now(UTC)
    at = at or current
    community = community_status(db, now)
    period, historical = historical_status(at)
    live = weather_status()
    predicted = predicted_now(live, current)
    roads = [{
        "road_id": road_id,
        "community": community[road_id],
        "historical": historical[road_id],
        "weather": predicted[road_id],
    } for road_id in MAIN_ROADS]
    return {
        "generated_at": current.isoformat(),
        "sources": {
            "community": {"window_hours": COMMUNITY_WINDOW_SECONDS // 3600, "data_source": "citizen reports"},
            "historical": {"data_source": HISTORY["data_source"], "notice": HISTORY["notice"],
                           "at": at.astimezone(DHAKA).isoformat(), **period, "bands": BANDS},
            "weather": {"data_source": "Open-Meteo + synthetic history", "status": live["status"],
                        "fetched_at": live["fetched_at"], "city": live.get("city"),
                        "estimate": "current rain from Open-Meteo applied to the history for this hour and rain",
                        **({"message": live["message"]} if "message" in live else {})},
        },
        "avoid_now": avoid_now(community, predicted),
        "roads": roads,
    }
