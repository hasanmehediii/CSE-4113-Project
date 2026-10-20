import csv
import shutil
from datetime import datetime

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.road_features import DATASET_FEATURES, dataset_features
from app.models.road_risk import RoadRiskModel
from app.train_road_dataset import (
    DEFAULT_DATASET,
    NODES,
    OBSERVATIONS,
    SEGMENTS,
    read_dataset,
    train,
    validation_thresholds,
)


@pytest.fixture(scope="module")
def supplied_model(tmp_path_factory):
    output = tmp_path_factory.mktemp("bilingual-model") / "model.joblib"
    report = train(DEFAULT_DATASET, output)
    return RoadRiskModel.load(output), report


def test_dataset_uses_fixed_time_partitions_and_serving_features():
    rows, matrix, labels, masks, profiles, _ = read_dataset(DEFAULT_DATASET)
    assert matrix.shape == (20790, 13)
    assert labels.shape == (20790, 2)
    assert [int(masks[s].sum()) for s in ("train", "validation", "test")] == [7560, 7560, 5670]
    assert not any(name.startswith("target_") for name in DATASET_FEATURES)
    assert len(profiles) == 210
    first = rows[0]
    expected = dataset_features(datetime.fromisoformat(first["target_time_dhaka"]),
                                float(first["forecast_rain_target_1h_mm_sim"]),
                                profiles[first["road_segment_id"]], int(first["forecast_horizon_min"]))
    np.testing.assert_allclose(matrix[0], expected)


def corrupted_copy(tmp_path, mutate):
    for name in (NODES, SEGMENTS):
        shutil.copyfile(DEFAULT_DATASET / name, tmp_path / name)
    with (DEFAULT_DATASET / OBSERVATIONS).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns, rows = reader.fieldnames, list(reader)
    mutate(rows)
    with (tmp_path / OBSERVATIONS).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize(("field", "value", "match"), [
    ("road_segment_id", "MISSING", "unknown segment"),
    ("forecast_horizon_min", "45", "forecast horizon"),
    ("target_any_blocked", "1", "inconsistent future labels"),
    ("forecast_rain_target_1h_mm_sim", "NaN", "Invalid forecast_rain"),
    ("data_origin", "REAL", "synthetic provenance"),
])
def test_invalid_dataset_never_replaces_working_artifact(tmp_path, field, value, match):
    corrupted_copy(tmp_path, lambda rows: rows[0].update({field: value}))
    output = tmp_path / "model.joblib"
    output.write_bytes(b"existing model")
    with pytest.raises(ValueError, match=match):
        train(tmp_path, output)
    assert output.read_bytes() == b"existing model"


def test_duplicate_record_is_rejected(tmp_path):
    corrupted_copy(tmp_path, lambda rows: rows[1].update(record_id=rows[0]["record_id"]))
    with pytest.raises(ValueError, match="Duplicate record"):
        read_dataset(tmp_path)


def test_overlapping_time_partitions_are_rejected(tmp_path):
    def move_validation_before_training(rows):
        row = next(row for row in rows if row["dataset_split"] == "validation")
        row["target_time_dhaka"] = "2023-01-01T08:00:00+06:00"
        from datetime import timedelta
        at = datetime.fromisoformat(row["target_time_dhaka"])
        row["issue_time_dhaka"] = (at - timedelta(minutes=int(row["forecast_horizon_min"]))).isoformat()

    corrupted_copy(tmp_path, move_validation_before_training)
    with pytest.raises(ValueError, match="Temporal partitions overlap"):
        read_dataset(tmp_path)


def test_training_report_and_mapped_inference(supplied_model):
    model, report = supplied_model
    assert report["serving_training_rows"] == 15120
    assert report["test_rows"] == 5670
    assert report["mapped_segments"] == 82
    assert report["data_source"] == "synthetic"
    assert set(report["evaluation"]) == {"waterlogging", "traffic_jam"}
    at = datetime.fromisoformat("2026-10-20T18:00:00+06:00")
    result = model.predict(at, 40, 30)
    assert len(result["roads"]) == 14
    assert result["issue_time"] == "2026-10-20T17:30:00+06:00"
    assert result["aggregation"] == "maximum_segment_probability"
    assert result["coverage"]["trained_segments"] == 210
    for row in result["roads"]:
        assert set(row["segment_ids"]) <= set(model.profiles)
        assert 0 <= row["waterlogging_probability"] <= 1
        assert 0 <= row["traffic_probability"] <= 1


def test_feature_timezone_parity_and_validation_thresholds():
    rows, _, _, _, profiles, _ = read_dataset(DEFAULT_DATASET)
    profile = profiles[rows[0]["road_segment_id"]]
    utc = datetime.fromisoformat("2026-10-20T02:00:00+00:00")
    dhaka = datetime.fromisoformat("2026-10-20T08:00:00+06:00")
    assert dataset_features(utc, 20, profile) == dataset_features(dhaka, 20, profile)
    thresholds = validation_thresholds(np.asarray([[0, 1], [1, 0]]), np.asarray([[.1, .8], [.7, .2]]))
    assert .1 < thresholds["waterlogging"] <= .7


def test_bilingual_model_api_and_horizon_validation(supplied_model):
    with TestClient(app) as client:
        app.state.road_risk = supplied_model[0]
        result = client.post("/road-risk/predict", json={"at": "2026-10-20T18:00:00+06:00", "forecast_horizon_min": 120})
        assert result.status_code == 200
        assert result.json()["forecast_horizon_min"] == 120
        assert client.get("/road-risk/model").json()["segments"] == 210
        result = client.post("/road-risk/predict", json={"at": "2026-10-20T18:00:00+06:00", "forecast_horizon_min": 45})
        assert result.status_code == 422
