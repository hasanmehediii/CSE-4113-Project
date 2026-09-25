import csv

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.models.classifier import CATEGORIES, ComplaintClassifier
from app.train import DEFAULT_DATASET, read_dataset, train


@pytest.fixture(scope="module")
def trained_artifact(tmp_path_factory):
    path = tmp_path_factory.mktemp("model") / "classifier.joblib"
    report = train(DEFAULT_DATASET, path)
    return path, report


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["id", "text_bn", "category"])
        writer.writerows(rows)


def test_training_and_reload(trained_artifact):
    path, report = trained_artifact
    model = ComplaintClassifier.load(path)
    prediction = model.predict("ম্যানহোলের ঢাকনা নেই, বাচ্চারা পড়ে যেতে পারে।")
    assert prediction["predicted_category"] == "open_manhole"
    assert set(prediction["probabilities"]) == set(CATEGORIES)
    assert sum(prediction["probabilities"].values()) == pytest.approx(1)
    assert 0 <= prediction["confidence"] <= 1
    assert prediction["data_source"] == "synthetic"
    assert (
        report["evaluation"]["test_rows"] + report["evaluation"]["train_rows"]
        == report["unique_rows"]
    )
    assert report["serving_model_training_rows"] == report["unique_rows"]
    assert path.with_suffix(".report.json").is_file()


def test_duplicate_texts_removed(tmp_path):
    rows = []
    for category in CATEGORIES:
        rows.extend(
            [
                (f"{category}-1", f"প্রথম {category}", category),
                (f"{category}-2", f"দ্বিতীয় {category}", category),
            ]
        )
    rows.append(("extra", "  প্রথম   blocked_drain  ", "blocked_drain"))
    path = tmp_path / "data.csv"
    write_csv(path, rows)
    texts, labels, stats = read_dataset(path)
    assert len(texts) == len(labels) == 12
    assert stats["duplicates_removed"] == 1


@pytest.mark.parametrize(
    "rows, message",
    [
        ([("1", " ", "other")], "text_bn"),
        ([("1", "অভিযোগ", "invalid")], "unknown category"),
        ([("1", "অভিযোগ", "other"), ("1", "দ্বিতীয়", "other")], "unique"),
        ([("1", "অভিযোগ", "other"), ("2", "অভিযোগ", "blocked_drain")], "conflicting"),
        ([("1", "অভিযোগ", "other")], "six categories"),
    ],
)
def test_bad_data_rejected(tmp_path, rows, message):
    path = tmp_path / "bad.csv"
    write_csv(path, rows)
    with pytest.raises(ValueError, match=message):
        read_dataset(path)


def test_missing_columns_rejected(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("text,label\nhello,other\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columns"):
        read_dataset(path)


def test_invalid_retraining_preserves_model(tmp_path, trained_artifact):
    path = tmp_path / "classifier.joblib"
    path.write_bytes(trained_artifact[0].read_bytes())
    previous = path.read_bytes()
    bad_data = tmp_path / "bad.csv"
    bad_data.write_text("wrong,columns\n", encoding="utf-8")
    with pytest.raises(ValueError):
        train(bad_data, path)
    assert path.read_bytes() == previous


def test_classify_api(monkeypatch, trained_artifact):
    monkeypatch.setenv("ML_MODEL_PATH", str(trained_artifact[0]))
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            assert client.get("/ready").status_code == 200
            response = client.post("/classify", json={"text": "ম্যানহোলের ঢাকনা নেই।"})
            assert response.status_code == 200
            assert response.json()["predicted_category"] == "open_manhole"
            assert client.get("/model").json()["data_source"] == "synthetic"
            for payload in ({"text": " "}, {"text": "x" * 5001}, {}, {"text": 42}):
                assert client.post("/classify", json=payload).status_code == 422
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("corrupt", [False, True])
def test_unavailable_model_returns_503(tmp_path, monkeypatch, corrupt):
    path = tmp_path / "missing.joblib"
    if corrupt:
        path.write_bytes(b"invalid artifact")
    monkeypatch.setenv("ML_MODEL_PATH", str(path))
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/ready").status_code == 503
            assert client.get("/model").status_code == 503
            assert client.post("/classify", json={"text": "অভিযোগ"}).status_code == 503
    finally:
        get_settings.cache_clear()


def test_default_model_path_is_absolute():
    assert Settings().model_path.is_absolute()
