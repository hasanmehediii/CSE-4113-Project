import io
import json
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError

import pytest
import test_civic
from sqlalchemy import func, select

from app.models.civic import Road
from app.services.road_catalog import MAIN_ROADS, seed_main_roads


@pytest.fixture
def map_env(tmp_path, monkeypatch):
    yield from test_civic.civic_env.__wrapped__(tmp_path, monkeypatch)


def test_catalog_is_idempotent_and_main_only(map_env):
    client, factory = map_env
    with factory() as db:
        seed_main_roads(db)
        seed_main_roads(db)
        assert db.scalar(select(func.count()).select_from(Road)) == len(MAIN_ROADS)
        road = db.get(Road, next(iter(MAIN_ROADS)))
        db.add(Road(name="Residential lane", area_id=road.area_id, latitude=23.8, longitude=90.4))
        db.commit()
    rows = client.get("/api/v1/map/roads?main_only=true").json()
    assert len(rows) == len(MAIN_ROADS)
    assert all(len(row["path"]) >= 2 and row["condition"] == "unknown" for row in rows)
    for row in rows:
        assert row["geometry_source"] == "openstreetmap"
        assert row["geometry_attribution"] == "© OpenStreetMap contributors"
        assert row["paths"] and all(len(path) >= 2 for path in row["paths"])
        assert [row["latitude"], row["longitude"]] in [point for path in row["paths"] for point in path]
    assert len(client.get("/api/v1/map/roads").json()) == len(MAIN_ROADS) + 1


def test_selected_road_update_persists_and_clear_does_not_close_complaint(map_env):
    client, factory = map_env
    with factory() as db:
        seed_main_roads(db)
        db.commit()
    road = client.get("/api/v1/map/roads?main_only=true").json()[0]
    user = test_civic.account(factory, "road-observer")
    test_civic.sign_in(client, factory, user)
    payload = {"road_id": road["id"], "latitude": road["latitude"], "longitude": road["longitude"],
               "category_code": "road_flooding", "kind": "road_update", "condition": "good",
               "title": "Road is currently passable", "description": "No standing water at this junction.",
               "address": road["name"]}
    assert client.post("/api/v1/complaints", headers=test_civic.headers(client), json=payload).status_code == 201
    rows = client.get("/api/v1/map/roads?main_only=true").json()
    assert next(row for row in rows if row["id"] == road["id"])["condition"] == "good"
    payload.update(kind="complaint", condition="bad")
    assert client.post("/api/v1/complaints", headers=test_civic.headers(client), json=payload).status_code == 201
    payload.update(kind="road_update", condition="good")
    assert client.post("/api/v1/complaints", headers=test_civic.headers(client), json=payload).status_code == 201
    rows = client.get("/api/v1/map/roads?main_only=true").json()
    assert next(row for row in rows if row["id"] == road["id"])["condition"] == "bad"


def test_old_database_center_is_repaired_without_changing_road_identity(map_env):
    client, factory = map_env
    road_id = "dhaka-airport-north"
    with factory() as db:
        seed_main_roads(db)
        road = db.get(Road, road_id)
        road.latitude, road.longitude = 23.837, 90.416
        db.commit()
    rows = client.get("/api/v1/map/roads?main_only=true").json()
    row = next(row for row in rows if row["id"] == road_id)
    assert [row["latitude"], row["longitude"]] == MAIN_ROADS[road_id]["center"]
    with factory() as db:
        seed_main_roads(db)
        road = db.get(Road, road_id)
        assert [road.latitude, road.longitude] == MAIN_ROADS[road_id]["center"]


def test_prediction_proxy_validation_and_unavailability(map_env, monkeypatch):
    client, _ = map_env
    at = datetime.now(UTC).isoformat()
    captured = []

    def upstream(request, timeout):
        captured.append(json.loads(request.data))
        return io.BytesIO(json.dumps({"data_source": "synthetic", "roads": []}).encode())

    monkeypatch.setattr("app.api.v1.map.urlopen", upstream)
    result = client.get("/api/v1/map/predictions", params={"at": at, "rainfall_mm": 25, "forecast_horizon_min": 30})
    assert result.status_code == 200
    assert captured[0]["rainfall_mm"] == 25
    assert captured[0]["forecast_horizon_min"] == 30
    assert result.json()["data_source"] == "synthetic"
    for params in ({"at": at, "rainfall_mm": "NaN"}, {"at": at, "rainfall_mm": 151},
                   {"at": at, "forecast_horizon_min": 45},
                   {"at": "2026-10-20T08:00:00"},
                   {"at": (datetime.now(UTC) + timedelta(days=8)).isoformat()}):
        assert client.get("/api/v1/map/predictions", params=params).status_code == 422

    def unavailable(*args, **kwargs):
        raise URLError("offline")

    monkeypatch.setattr("app.api.v1.map.urlopen", unavailable)
    assert client.get("/api/v1/map/predictions", params={"at": at}).status_code == 503


@pytest.mark.parametrize("failure, status, expected", [
    # ML is stopped: say so instead of asking to train a model.
    (URLError("connection refused"), 503, "not reachable. Start the ML service"),
    (TimeoutError(), 503, "not reachable. Start the ML service"),
    # ML runs but its model is missing/incompatible: keep the ML reason.
    (HTTPError("http://ml/road-risk/predict", 503, "Service Unavailable", {}, io.BytesIO(json.dumps({
        "detail": "Road-risk model unavailable: road-risk.joblib is incompatible: Artifact mapping does not match "
                  "the current map catalog."}).encode())), 503, "does not match the current map catalog"),
    (HTTPError("http://ml/road-risk/predict", 503, "Service Unavailable", {}, io.BytesIO(b"not json")),
     503, "The road-risk model is not loaded."),
    (HTTPError("http://ml/road-risk/predict", 500, "Server Error", {}, io.BytesIO(b"{}")), 502, "(HTTP 500)"),
])
def test_prediction_failures_explain_the_cause(map_env, monkeypatch, failure, status, expected):
    client, _ = map_env

    def upstream(request, timeout):
        raise failure

    monkeypatch.setattr("app.api.v1.map.urlopen", upstream)
    response = client.get("/api/v1/map/predictions", params={"at": datetime.now(UTC).isoformat()})
    assert response.status_code == status
    assert expected in response.json()["detail"]
    assert "Train the road-risk model and start" not in response.json()["detail"]


@pytest.mark.parametrize("body", [b"not json", b"[]", b'{"roads": null}'])
def test_prediction_rejects_malformed_ml_response(map_env, monkeypatch, body):
    client, _ = map_env
    monkeypatch.setattr("app.api.v1.map.urlopen", lambda request, timeout: io.BytesIO(body))
    response = client.get("/api/v1/map/predictions", params={"at": datetime.now(UTC).isoformat()})
    assert response.status_code == 502
    assert "invalid prediction response" in response.json()["detail"]
