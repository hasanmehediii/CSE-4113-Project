"""Generate reproducible hourly scenarios, evaluate by date, then train for serving.

Run: python -m app.train_road_risk
The generated CSV and model live in gitignored weights/. No real observations implied.
"""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, f1_score

from app.core.config import get_settings
from app.models.road_risk import CATALOG, DHAKA, FEATURES, features


def generate_dataset(path: Path, days=365, seed=42):
    rng = np.random.default_rng(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2025, 1, 1, tzinfo=DHAKA)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["road_id", "at", "rainfall_mm", "waterlogging", "traffic_jam"])
        for day in range(days):
            for hour in range(24):
                at = start + timedelta(days=day, hours=hour)
                monsoon = 5 <= at.month <= 10
                # City-wide scenario rain, not measured weather.
                rain = round(float(min(150, rng.gamma(2, 12) if rng.random() < (.4 if monsoon else .1) else 0)), 2)
                for road in CATALOG:
                    flood_logit = -4.5 + rain * .09 + road["flood_factor"] * 2
                    rush = 7 <= hour <= 10 or 16 <= hour <= 20
                    weekday = at.weekday() not in (4, 5)  # Bangladesh weekend
                    traffic_logit = -3.8 + road["traffic_factor"] * 2 + 2.4 * rush + .8 * weekday + rain * .018
                    flood = int(rng.random() < 1 / (1 + np.exp(-flood_logit)))
                    traffic = int(rng.random() < 1 / (1 + np.exp(-traffic_logit)))
                    writer.writerow([road["id"], at.isoformat(), rain, flood, traffic])


def train(dataset: Path, output: Path):
    catalog = {r["id"]: r for r in CATALOG}
    matrix, labels, timestamps = [], [], []
    seen = set()
    with dataset.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            at = datetime.fromisoformat(row["at"])
            rain = float(row["rainfall_mm"])
            targets = [int(row["waterlogging"]), int(row["traffic_jam"])]
            key = (row["road_id"], at.timestamp())
            if (at.tzinfo is None or key in seen or row["road_id"] not in catalog
                    or not np.isfinite(rain) or not 0 <= rain <= 150
                    or any(v not in (0, 1) for v in targets)):
                raise ValueError("Invalid, duplicate, or unsupported road-risk observation")
            seen.add(key)
            matrix.append(features(at, rain, catalog[row["road_id"]]))
            labels.append(targets)
            timestamps.append(at.timestamp())
    if len(matrix) < 100:
        raise ValueError("At least 100 observations required")
    x, y, times = np.asarray(matrix), np.asarray(labels), np.asarray(timestamps)
    cutoff = np.quantile(np.unique(times), .8)
    earlier, later = times < cutoff, times >= cutoff
    if not earlier.any() or not later.any():
        raise ValueError("Dataset must span multiple timestamps")
    model = RandomForestClassifier(n_estimators=64, max_depth=12, min_samples_leaf=25,
                                   random_state=42, n_jobs=-1)
    model.fit(x[earlier], y[earlier])
    probability = model.predict_proba(x[later])
    evaluation = {}
    for i, name in enumerate(("waterlogging", "traffic_jam")):
        classes = list(model.classes_[i])
        p = probability[i][:, classes.index(1)] if 1 in classes else np.zeros(later.sum())
        evaluation[name] = {"f1": round(float(f1_score(y[later, i], p >= .5, zero_division=0)), 4),
                            "brier_score": round(float(brier_score_loss(y[later, i], p)), 4)}
    digest = hashlib.sha256(dataset.read_bytes()).hexdigest()
    metadata = {"model_version": f"road-risk-synthetic-v1-{digest[:12]}",
                "data_source": "synthetic", "dataset_sha256": digest,
                "rows": len(y), "train_rows": int(earlier.sum()), "holdout_rows": int(later.sum()),
                "evaluation": evaluation, "split": "chronological 80/20, all roads grouped by timestamp",
                "limitations": "Simulated labels and assumed road factors; metrics only measure learning the simulator. Probabilities are uncalibrated. No real-world validity established."}
    model.fit(x, y)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    joblib.dump({"format": 1, "features": FEATURES, "model": model, "metadata": metadata}, temporary)
    temporary.replace(output)
    output.with_suffix(".report.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--dataset", type=Path, help="Bilingual dataset folder (defaults to packages/new-data when present)")
    parser.add_argument("--output", type=Path, help="Artifact output path")
    parser.add_argument("--generate", action="store_true", help="Use the legacy generated hourly dataset instead")
    args = parser.parse_args()
    if args.generate and args.dataset:
        parser.error("Use either --generate or --dataset")
    if not 7 <= args.days <= 730:
        parser.error("--days must be between 7 and 730")
    output = args.output or get_settings().road_risk_model_path
    from app.train_road_dataset import DEFAULT_DATASET
    from app.train_road_dataset import train as train_supplied

    if args.dataset or (DEFAULT_DATASET.is_dir() and not args.generate):
        report = train_supplied(args.dataset or DEFAULT_DATASET, output)
        print(json.dumps({key: value for key, value in report.items()
                          if key not in {"evaluation_by_corridor", "evaluation_by_month", "candidates"}}, indent=2))
        return
    dataset = output.parent / "road_risk_synthetic.csv"
    generate_dataset(dataset, args.days)
    print(json.dumps(train(dataset, output), indent=2))


if __name__ == "__main__":
    main()
