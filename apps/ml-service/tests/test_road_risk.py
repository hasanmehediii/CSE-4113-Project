from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.road_risk import CATALOG, RoadRiskModel, features
from app.train_road_risk import generate_dataset, train


@pytest.fixture(scope="module")
def road_model(tmp_path_factory):
    folder = tmp_path_factory.mktemp("road-risk")
    dataset, artifact = folder / "scenarios.csv", folder / "road-risk.joblib"
    generate_dataset(dataset, days=14)
    report = train(dataset, artifact)
    return RoadRiskModel.load(artifact), report


def test_timezones_produce_identical_features():
    utc = datetime.fromisoformat("2026-10-20T02:00:00+00:00")
    dhaka = datetime.fromisoformat("2026-10-20T08:00:00+06:00")
    assert features(utc, 20, CATALOG[0]) == features(dhaka, 20, CATALOG[0])


def test_dataset_split_and_rain_response(road_model):
    model, report = road_model
    assert report["rows"] == 14 * 24 * len(CATALOG)
    assert report["train_rows"] + report["holdout_rows"] == report["rows"]
    at = datetime.fromisoformat("2026-10-20T08:00:00+06:00")
    dry, wet = model.predict(at, 0), model.predict(at, 90)
    assert dry["data_source"] == "synthetic"
    assert dry["timezone"] == "Asia/Dhaka"
    assert {r["road_id"] for r in dry["roads"]} == {r["id"] for r in CATALOG}
    assert sum(r["waterlogging_probability"] for r in wet["roads"]) > sum(
        r["waterlogging_probability"] for r in dry["roads"])
    for row in wet["roads"]:
        assert 0 <= row["waterlogging_probability"] <= 1
        assert 0 <= row["traffic_probability"] <= 1


def test_inference_and_input_validation(road_model):
    with TestClient(app) as client:
        app.state.road_risk = road_model[0]
        assert client.post("/road-risk/predict", json={"at": "2026-10-20T08:00:00+06:00"}).status_code == 200
        for body in ({"at": "2026-10-20T08:00:00"},
                     {"at": "2026-10-20T08:00:00+06:00", "rainfall_mm": -1},
                     {"at": "2026-10-20T08:00:00+06:00", "rainfall_mm": 151}):
            assert client.post("/road-risk/predict", json=body).status_code == 422
        app.state.road_risk = None
        assert client.post("/road-risk/predict", json={"at": "2026-10-20T08:00:00+06:00"}).status_code == 503
        assert client.get("/health").status_code == 200
