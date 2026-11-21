import json

import joblib
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.models.road_features import DATASET_FEATURES
from app.models.road_risk import SEGMENT_MAPPING, RoadRiskModel
from app.train import DEFAULT_DATASET, train

AT = {"at": "2026-10-20T08:00:00+06:00", "rainfall_mm": 20}


@pytest.fixture(scope="module")
def classifier_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("diagnostics") / "classifier.joblib"
    train(DEFAULT_DATASET, path)
    return path


@pytest.fixture
def service(monkeypatch):
    def start(classifier, road_risk):
        monkeypatch.setenv("ML_MODEL_PATH", str(classifier))
        monkeypatch.setenv("ML_ROAD_RISK_MODEL_PATH", str(road_risk))
        get_settings.cache_clear()
        return TestClient(app)

    yield start
    get_settings.cache_clear()


def detail(response):
    assert response.status_code == 503
    return response.json()["detail"]


def test_missing_models_name_the_file_and_training_command(service, tmp_path):
    with service(tmp_path / "classifier.joblib", tmp_path / "road-risk.joblib") as client:
        assert client.get("/health").status_code == 200
        ready = detail(client.get("/ready"))
        assert "classifier.joblib was not found" in ready and "python -m app.train" in ready
        assert detail(client.get("/model")) == ready
        assert detail(client.post("/classify", json={"text": "অভিযোগ"})) == ready
        road = detail(client.post("/road-risk/predict", json=AT))
        assert "road-risk.joblib was not found" in road and "python -m app.train_road_risk" in road
        assert detail(client.get("/road-risk/model")) == road


def test_corrupt_classifier_is_not_reported_as_missing(service, tmp_path):
    corrupt = tmp_path / "classifier.joblib"
    corrupt.write_bytes(b"not a joblib artifact")
    with service(corrupt, tmp_path / "road-risk.joblib") as client:
        ready = detail(client.get("/ready"))
        assert "could not be read" in ready and "not found" not in ready
        assert "startup never replaces an existing file" in ready


@pytest.mark.parametrize("artifact, reason", [
    # A catalog edit without retraining: the saved road mapping no longer matches.
    ({"format": 2, "features": DATASET_FEATURES, "model": None, "metadata": {},
      "profiles": {}, "road_segments": {}}, "does not match the current map catalog"),
    ({"format": 9, "features": []}, "Incompatible road-risk artifact"),
])
def test_incompatible_road_risk_explains_reason(service, tmp_path, classifier_path, artifact, reason):
    road_risk = tmp_path / "road-risk.joblib"
    joblib.dump(artifact, road_risk)
    with service(classifier_path, road_risk) as client:
        message = detail(client.post("/road-risk/predict", json=AT))
        assert "road-risk.joblib is incompatible" in message and reason in message
        assert "python -m app.train_road_risk" in message
        # The classifier stays ready and reports the road-risk problem for diagnosis.
        ready = client.get("/ready")
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"
        assert ready.json()["road_risk_model"] == message


def test_ready_reports_loaded_road_risk(service, classifier_path):
    with service(classifier_path, classifier_path.parent / "missing.joblib") as client:
        app.state.road_risk = object()
        assert client.get("/ready").json()["road_risk_model"] == "loaded"


def mapped_artifact(roads):
    """A loadable format-2 artifact; loading only checks structure, not the fitted model."""
    segments = {s for ids in roads.values() for s in ids}
    return {"format": 2, "features": DATASET_FEATURES, "model": None, "metadata": {},
            "profiles": {s: {} for s in segments}, "road_segments": roads}


def test_saved_segment_mapping_must_match_the_deployment_mapping(service, tmp_path, classifier_path):
    # Issue #11: a model saved before a mapping change must not silently serve old segments.
    current = json.loads(SEGMENT_MAPPING.read_text("utf-8"))["roads"]
    assert RoadRiskModel(mapped_artifact(current)).road_segments == current
    stale = {road: list(ids) for road, ids in current.items()}
    stale["dhaka-manik-mia"] = stale["dhaka-manik-mia"][:-2] or ["DHK001A", "DHK001B"]
    road_risk = tmp_path / "road-risk.joblib"
    joblib.dump(mapped_artifact(stale), road_risk)
    with service(classifier_path, road_risk) as client:
        message = detail(client.get("/road-risk/model"))
        assert "road-risk.joblib is incompatible" in message
        assert "differs from dhaka-road-segment-mapping.json for dhaka-manik-mia" in message
        assert detail(client.post("/road-risk/predict", json=AT)) == message
