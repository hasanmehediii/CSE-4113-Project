import io
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import URLError

import pytest
import test_civic
from sqlalchemy import update

from app.models.civic import Complaint
from app.services import road_status as rs
from app.services.road_catalog import MAIN_ROADS, seed_main_roads

ROAD, OTHER = "dhaka-rokeya", "dhaka-gulshan"


@pytest.fixture
def status_env(tmp_path, monkeypatch):
    rs.clear_weather_cache()
    gen = test_civic.civic_env.__wrapped__(tmp_path, monkeypatch)
    client, factory = next(gen)
    with factory() as db:
        seed_main_roads(db)
        db.commit()
    test_civic.sign_in(client, factory, test_civic.account(factory, "road-reporter"))
    yield client, factory
    rs.clear_weather_cache()
    next(gen, None)


def report(client, factory, road_id, category, *, kind="complaint", condition="bad", age_seconds=0,
           title="Road report from a citizen"):
    road = MAIN_ROADS[road_id]
    response = client.post("/api/v1/complaints", headers=test_civic.headers(client), json={
        "road_id": road_id, "latitude": road["center"][0], "longitude": road["center"][1],
        "category_code": category, "kind": kind, "condition": condition, "title": title,
        "description": "Synthetic report for the road status test.", "address": road["name"],
        "separate_incident": kind == "complaint"})
    assert response.status_code == 201, response.text
    report_id = response.json()["id"]
    with factory() as db:
        db.execute(update(Complaint).where(Complaint.id == report_id)
                   .values(created_at=int(time.time()) - age_seconds))
        db.commit()
    return report_id


def statuses(client):
    response = client.get("/api/v1/map/road-status")
    assert response.status_code == 200
    return response.json(), {row["road_id"]: row for row in response.json()["roads"]}


def test_community_status_uses_only_the_last_four_hours(status_env, monkeypatch):
    client, factory = status_env
    monkeypatch.setattr(rs, "_fetch_open_meteo", lambda: {"roads": {}, "city": None})
    report(client, factory, ROAD, "road_flooding", age_seconds=4 * 3600 - 60)          # inside the window
    report(client, factory, ROAD, "traffic_jam", kind="road_update", age_seconds=4 * 3600 + 60)  # expired
    body, roads = statuses(client)
    water, traffic = roads[ROAD]["community"]["waterlogging"], roads[ROAD]["community"]["traffic"]
    assert water["status"] == "reported" and water["reports"] == 1
    assert water["expires_at"] == water["last_report_at"] + 4 * 3600
    assert traffic["status"] == "none" and traffic["reports"] == 0
    assert body["sources"]["community"]["window_hours"] == 4
    assert roads[OTHER]["community"]["waterlogging"]["status"] == "none"


def test_latest_report_decides_and_false_reports_are_ignored(status_env, monkeypatch):
    client, factory = status_env
    monkeypatch.setattr(rs, "_fetch_open_meteo", lambda: {"roads": {}, "city": None})
    report(client, factory, OTHER, "traffic_jam", kind="road_update", age_seconds=7200)
    report(client, factory, OTHER, "traffic_jam", kind="road_update", condition="good", age_seconds=3600)
    false_id = report(client, factory, ROAD, "road_flooding", age_seconds=600)
    # Older traffic reports from the road form used "other" with this title.
    report(client, factory, ROAD, "other", kind="road_update", age_seconds=300,
           title="Begum Rokeya Sarani — Traffic / obstruction · Needs attention")
    report(client, factory, ROAD, "road_damage", age_seconds=200)                     # neither hazard
    with factory() as db:
        db.execute(update(Complaint).where(Complaint.id == false_id).values(status="false"))
        db.commit()
    _, roads = statuses(client)
    gulshan = roads[OTHER]["community"]["traffic"]
    assert gulshan["status"] == "clear" and gulshan["reports"] == 1 and gulshan["clear_reports"] == 1
    assert gulshan["expires_at"] is None
    assert roads[ROAD]["community"]["waterlogging"]["status"] == "none"
    assert roads[ROAD]["community"]["traffic"]["status"] == "reported"


@pytest.mark.parametrize("at, season, day_type", [
    ("2026-07-13T18:30:00+06:00", "monsoon", "workday"),       # Monday
    ("2026-07-17T09:00:00+06:00", "monsoon", "friday"),
    ("2026-01-10T08:00:00+06:00", "dry", "saturday"),
    ("2026-07-13T02:30:00+00:00", "monsoon", "workday"),       # 08:30 in Dhaka
])
def test_historical_profile_matches_season_day_and_hour(at, season, day_type):
    moment = datetime.fromisoformat(at)
    period, roads = rs.historical_status(moment)
    hour = moment.astimezone(rs.DHAKA).hour
    assert period == {"season": season, "day_type": day_type, "hour": hour}
    expected = rs.HISTORY["roads"][ROAD]["traffic"][season][day_type]["any"][hour]
    assert roads[ROAD]["traffic"] == {"probability": expected, "level": rs.level_for("traffic", expected)}
    assert set(roads) == set(MAIN_ROADS)


def test_history_file_matches_its_generator():
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run([sys.executable, str(root / "scripts/generate-road-history.py"), "--check"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert rs.HISTORY["data_source"] == "synthetic"
    assert set(rs.HISTORY["roads"]) == set(MAIN_ROADS)


def test_levels_and_rain_bands():
    assert rs.level_for("traffic", 0.6) == "high" and rs.level_for("traffic", 0.3) == "moderate"
    assert rs.level_for("waterlogging", 0.25) == "high" and rs.level_for("waterlogging", 0.09) == "low"
    assert [rs.rain_band(mm) for mm in (0, 0.4, 0.5, 7.9, 8, 40)] == ["none", "none", "light", "light", "heavy", "heavy"]


def test_open_meteo_response_is_parsed_per_road_and_for_the_city(monkeypatch):
    def location(hourly):
        return {"current": {"time": "2026-11-22T19:00", "precipitation": 0.0, "temperature_2m": 27.4, "weather_code": 61},
                "hourly": {"time": [f"2026-11-22T{h}:00" for h in range(13, 20)], "precipitation": hourly}}
    body = [location([0, 0, 0, 2, 5, 8, 9.9]) for _ in MAIN_ROADS] + [location([0, 0, 0, 0, 1, 1, 1])]
    captured = {}

    def upstream(request, timeout):
        captured["url"] = request.full_url
        return io.BytesIO(json.dumps(body).encode())

    monkeypatch.setattr(rs, "urlopen", upstream)
    fetched = rs._fetch_open_meteo()
    assert "api.open-meteo.com" in captured["url"] and "past_hours=6" in captured["url"]
    assert fetched["roads"][ROAD] == {"rain_mm_1h": 9.9, "rain_mm_3h": 22.9, "observed_at": "2026-11-22T19:00"}
    assert fetched["city"] == {"temperature_c": 27.4, "weather_code": 61, "rain_mm_1h": 1.0, "rain_mm_3h": 3.0,
                               "observed_at": "2026-11-22T19:00"}
    monkeypatch.setattr(rs, "urlopen", lambda request, timeout: io.BytesIO(json.dumps(body[:3]).encode()))
    with pytest.raises(ValueError):
        rs._fetch_open_meteo()


def test_now_combines_current_rain_with_the_matching_history():
    # Monday 18:00 in July: heavy rain must use the heavy-rain history, dry weather the dry one.
    now = datetime.fromisoformat("2026-07-13T18:00:00+06:00")
    live = {"roads": {ROAD: {"rain_mm_1h": 6.0, "rain_mm_3h": 20.0, "observed_at": "x"},
                      OTHER: {"rain_mm_1h": 0.0, "rain_mm_3h": 0.0, "observed_at": "x"}}}
    predicted = rs.predicted_now(live, now)
    history = rs.HISTORY["roads"]
    assert predicted[ROAD]["rain_band"] == "heavy"
    assert predicted[ROAD]["waterlogging"]["probability"] == history[ROAD]["waterlogging"]["monsoon"]["workday"]["heavy"][18]
    assert predicted[OTHER]["rain_band"] == "none"
    assert predicted[OTHER]["traffic"]["probability"] == history[OTHER]["traffic"]["monsoon"]["workday"]["none"][18]
    assert predicted["dhaka-vip"] is None                      # no weather for that road
    # In the generated history, heavy rain makes waterlogging far likelier than dry weather.
    road = history["dhaka-pragati"]["waterlogging"]["monsoon"]["workday"]
    assert road["heavy"][18] > road["none"][18] + 0.5


def test_avoid_now_lists_reported_roads_first_then_high_predictions():
    blank = {hazard: {"status": "none"} for hazard in rs.HAZARDS}
    community = {road_id: blank for road_id in MAIN_ROADS}
    community["dhaka-vip"] = {"traffic": {"status": "reported"}, "waterlogging": {"status": "clear"}}
    level = lambda traffic, water: {"traffic": {"level": traffic}, "waterlogging": {"level": water}}
    predicted = {road_id: level("low", "low") for road_id in MAIN_ROADS}
    predicted["dhaka-pragati"] = level("high", "high")
    predicted[OTHER] = level("moderate", "high")
    predicted["dhaka-bijoy"] = None
    rows = rs.avoid_now(community, predicted)
    assert rows[0] == {"road_id": "dhaka-vip", "reasons": ["reported_traffic"]}
    assert rows[1] == {"road_id": "dhaka-pragati", "reasons": ["likely_traffic", "likely_waterlogging"]}
    assert {"road_id": OTHER, "reasons": ["likely_waterlogging"]} in rows
    assert len(rows) == 3


def test_weather_is_cached_then_stale_then_unavailable():
    rs.clear_weather_cache()
    calls, clock = [], [1000.0]

    def ok():
        calls.append(1)
        return {"roads": {ROAD: {"rain_mm_1h": 1.0}}, "city": {"temperature_c": 30}}

    def down():
        raise URLError("offline")

    assert rs.weather_status(ok, lambda: clock[0])["status"] == "live"
    clock[0] += 300
    assert rs.weather_status(ok, lambda: clock[0])["status"] == "live" and len(calls) == 1
    clock[0] += 400                                                    # past the 10-minute cache
    stale = rs.weather_status(down, lambda: clock[0])
    assert stale["status"] == "stale" and stale["roads"][ROAD]["rain_mm_1h"] == 1.0
    clock[0] += 3600
    gone = rs.weather_status(down, lambda: clock[0])
    assert gone["status"] == "unavailable" and gone["roads"] == {} and gone["city"] is None
    rs.clear_weather_cache()


def test_endpoint_keeps_other_sources_when_weather_is_down(status_env, monkeypatch):
    client, factory = status_env

    def down():
        raise URLError("offline")

    monkeypatch.setattr(rs, "_fetch_open_meteo", down)
    report(client, factory, ROAD, "road_flooding", age_seconds=60)
    body, roads = statuses(client)
    assert body["sources"]["weather"]["status"] == "unavailable"
    assert "not available" in body["sources"]["weather"]["message"]
    assert roads[ROAD]["weather"] is None
    assert roads[ROAD]["community"]["waterlogging"]["status"] == "reported"
    # Actual (reported) conditions still put the road on the avoid list without weather.
    assert {"road_id": ROAD, "reasons": ["reported_waterlogging"]} in body["avoid_now"]
    assert roads[ROAD]["historical"]["traffic"]["level"] in {"high", "moderate", "low"}
    assert body["sources"]["historical"]["data_source"] == "synthetic"
    assert client.get("/api/v1/map/road-status", params={"at": "2020-01-01T00:00:00+06:00"}).status_code == 422
