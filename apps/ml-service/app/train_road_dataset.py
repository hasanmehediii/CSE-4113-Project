"""Validate and train the supplied bilingual dataset without future outcome leakage."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_fscore_support,
)

from app.models.road_features import (
    DATASET_FEATURES,
    DHAKA,
    STATIC_COLUMNS,
    TARGETS,
    binary_probabilities,
    dataset_features,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET = REPO_ROOT / "packages/new-data"
DEFAULT_MAPPING = REPO_ROOT / "packages/data/dhaka-road-segment-mapping.json"
OBSERVATIONS = "dhaka_major_roads_ml_dataset_bilingual.csv"
SEGMENTS = "dhaka_directed_road_segments_bilingual.csv"
NODES = "dhaka_major_road_nodes_bilingual.csv"
ORIGIN = "SYNTHETIC_SIMULATED_NOT_OBSERVED"


def read_csv(path, required):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name}: no rows")
    return rows


def number(row, column, lower, upper):
    value = float(row[column])
    if not np.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"Invalid {column}: {row.get('record_id', row.get('segment_id'))}")
    return value


def read_dataset(folder: Path, mapping_path: Path = DEFAULT_MAPPING):
    folder = folder if folder.is_dir() else folder.parent
    nodes = read_csv(folder / NODES, ["node_id"])
    node_ids = {row["node_id"] for row in nodes}
    if len(node_ids) != len(nodes) or "" in node_ids:
        raise ValueError("Duplicate or empty junction ID")
    edges = read_csv(folder / SEGMENTS, ["segment_id", "from_node_id", "to_node_id",
                                      "corridor_name_en", "corridor_name_bn"])
    segments = {row["segment_id"]: row for row in edges}
    if len(segments) != len(edges) or "" in segments:
        raise ValueError("Duplicate or empty segment ID")
    if any(row["from_node_id"] not in node_ids or row["to_node_id"] not in node_ids for row in edges):
        raise ValueError("A segment references an unknown junction")
    required = ["record_id", "road_segment_id", "issue_time_dhaka", "target_time_dhaka",
                "forecast_horizon_min", "forecast_rain_target_1h_mm_sim", "dataset_split",
                "data_origin", "target_water_blocked", "target_traffic_blocked", "target_any_blocked",
                "corridor_name_en", "from_node_id", "to_node_id", *STATIC_COLUMNS]
    rows = read_csv(folder / OBSERVATIONS, required)
    order = {"train": 0, "validation": 1, "test": 2}
    rows.sort(key=lambda row: (order.get(row["dataset_split"], 3), row["target_time_dhaka"]))
    ids, seen, profiles, time_splits = set(), set(), {}, {}
    matrix, labels, splits, times, issue_times = [], [], [], [], []
    for row in rows:
        key, segment_id = row["record_id"], row["road_segment_id"]
        if not key or key in ids or segment_id not in segments:
            raise ValueError(f"Duplicate record or unknown segment: {key}")
        ids.add(key)
        edge = segments[segment_id]
        if any(row[c] != edge[c] for c in ("from_node_id", "to_node_id", "corridor_name_en")):
            raise ValueError(f"Segment lookup mismatch: {key}")
        if row["data_origin"] != ORIGIN:
            raise ValueError("This importer requires declared synthetic provenance")
        split = row["dataset_split"]
        if split not in {"train", "validation", "test"}:
            raise ValueError(f"Unknown dataset split: {split}")
        at, issue = (datetime.fromisoformat(row[c]) for c in ("target_time_dhaka", "issue_time_dhaka"))
        if any(t.tzinfo is None or t.utcoffset() != timedelta(hours=6) for t in (at, issue)):
            raise ValueError(f"Expected offset-aware Dhaka times: {key}")
        horizon = number(row, "forecast_horizon_min", 30, 120)
        if horizon not in (30, 60, 120) or (at - issue).total_seconds() != horizon * 60:
            raise ValueError(f"Invalid forecast horizon: {key}")
        observation = (segment_id, at.timestamp())
        if observation in seen:
            raise ValueError(f"Duplicate segment/time: {key}")
        seen.add(observation)
        if time_splits.setdefault(at.timestamp(), split) != split:
            raise ValueError("A shared scenario timestamp crosses split boundaries")
        profile = {c: number(row, c, *bounds) for c, bounds in STATIC_COLUMNS.items()}
        if profile["assumed_lane_count"] != int(profile["assumed_lane_count"]):
            raise ValueError(f"Non-integer lane count: {key}")
        if segment_id in profiles and any(profiles[segment_id][c] != profile[c] for c in STATIC_COLUMNS):
            raise ValueError(f"Static road features change across time: {segment_id}")
        if split == "train":
            profiles[segment_id] = {**edge, **profile}
        rain = number(row, "forecast_rain_target_1h_mm_sim", 0, 150)
        target = [int(row["target_water_blocked"]), int(row["target_traffic_blocked"])]
        if any(v not in (0, 1) for v in target) or int(row["target_any_blocked"]) != max(target):
            raise ValueError(f"Invalid or inconsistent future labels: {key}")
        matrix.append(dataset_features(at, rain, profile, int(horizon)))
        labels.append(target)
        splits.append(split)
        times.append(at.timestamp())
        issue_times.append(issue.timestamp())
    x, y, splits, times, issue_times = map(np.asarray, (matrix, labels, splits, times, issue_times))
    if set(profiles) != set(segments):
        raise ValueError("Every segment must have a training-period static profile")
    masks = {split: splits == split for split in ("train", "validation", "test")}
    if any(not mask.any() for mask in masks.values()):
        raise ValueError("Train, validation and test partitions must all be present")
    if (times[masks["train"]].max() >= issue_times[masks["validation"]].min()
            or times[masks["validation"]].max() >= issue_times[masks["test"]].min()):
        raise ValueError("Temporal partitions overlap, including the forecast horizon")
    if any(len(np.unique(y[masks["train"], i])) != 2 for i in range(2)):
        raise ValueError("Both classes are required for each training target")
    mapping = json.loads(mapping_path.read_text("utf-8"))
    catalog = json.loads((REPO_ROOT / "packages/data/dhaka-main-roads.json").read_text("utf-8"))
    if set(mapping["roads"]) != {road["id"] for road in catalog}:
        raise ValueError("Segment mapping must cover exactly the current map road IDs")
    for mapped in mapping["roads"].values():
        if not mapped or len(set(mapped)) != len(mapped) or not set(mapped) <= set(segments):
            raise ValueError("Empty, duplicate or unknown mapped segment")
    return rows, x, y, masks, profiles, mapping


def metrics(y, probabilities, thresholds=None):
    thresholds = thresholds or {name: .5 for name in TARGETS}
    result = {}
    for i, name in enumerate(TARGETS):
        actual, p = y[:, i], probabilities[:, i]
        threshold = thresholds[name]
        precision, recall, f1, _ = precision_recall_fscore_support(
            actual, p >= threshold, average="binary", zero_division=0)
        result[name] = {
            "rows": len(actual), "positives": int(actual.sum()),
            "threshold": threshold,
            "prevalence": round(float(actual.mean()), 6),
            "precision": round(float(precision), 6), "recall": round(float(recall), 6),
            "f1": round(float(f1), 6),
            "average_precision": round(float(average_precision_score(actual, p)), 6) if actual.any() else None,
            "brier_score": round(float(brier_score_loss(actual, p)), 6),
            "confusion_matrix_tn_fp_fn_tp": confusion_matrix(actual, p >= threshold, labels=[0, 1]).ravel().tolist(),
        }
    return result


def validation_thresholds(y, probabilities):
    """Rare blockage labels require an explicit validation-only decision threshold."""
    result = {}
    for i, name in enumerate(TARGETS):
        scores = []
        for threshold in np.arange(.05, .96, .05):
            _, _, f1, _ = precision_recall_fscore_support(
                y[:, i], probabilities[:, i] >= threshold, average="binary", zero_division=0)
            scores.append((float(f1), round(float(threshold), 2)))
        result[name] = max(scores)[1]
    return result


def train(folder: Path, output: Path, mapping_path: Path = DEFAULT_MAPPING):
    rows, x, y, masks, profiles, mapping = read_dataset(folder, mapping_path)
    candidates = []
    settings = [{"max_depth": 12, "min_samples_leaf": 5},
                {"max_depth": 10, "min_samples_leaf": 20}]
    for parameters in settings:
        model = RandomForestClassifier(n_estimators=128, random_state=42, n_jobs=-1, **parameters)
        model.fit(x[masks["train"]], y[masks["train"]])
        validation = metrics(y[masks["validation"]], binary_probabilities(model, x[masks["validation"]]))
        score = np.mean([validation[name]["average_precision"] for name in TARGETS])
        thresholds = validation_thresholds(y[masks["validation"]], binary_probabilities(model, x[masks["validation"]]))
        candidates.append({"parameters": parameters, "validation_at_0_5": validation,
                           "thresholds": thresholds,
                           "validation": metrics(y[masks["validation"]], binary_probabilities(model, x[masks["validation"]]), thresholds),
                           "selection_score": float(score)})
    best = max(candidates, key=lambda item: item["selection_score"])
    serving_mask = masks["train"] | masks["validation"]
    model = RandomForestClassifier(n_estimators=128, random_state=42, n_jobs=-1, **best["parameters"])
    model.fit(x[serving_mask], y[serving_mask])
    test_y = y[masks["test"]]
    test_probabilities = binary_probabilities(model, x[masks["test"]])
    test_rows = [row for row, selected in zip(rows, masks["test"], strict=True) if selected]
    by_corridor, by_month = {}, {}
    for field, grouped in (("corridor_name_en", by_corridor), ("month", by_month)):
        values = [row[field] if field != "month" else str(datetime.fromisoformat(row["target_time_dhaka"]).month) for row in test_rows]
        for value in sorted(set(values)):
            mask = np.asarray([v == value for v in values])
            grouped[value] = metrics(test_y[mask], test_probabilities[mask], best["thresholds"])
    folder = folder if folder.is_dir() else folder.parent
    hashes = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in (OBSERVATIONS, SEGMENTS, NODES)}
    mapping_hash = hashlib.sha256(mapping_path.read_bytes()).hexdigest()
    recipe_hash = hashlib.sha256(Path(__file__).read_bytes() +
                                 (Path(__file__).parent / "models/road_features.py").read_bytes()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps({**hashes, "mapping": mapping_hash,
        "features": DATASET_FEATURES, "training_code": recipe_hash,
        "scikit_learn": sklearn.__version__}, sort_keys=True).encode()).hexdigest()
    split_details = {}
    for split in masks:
        subset = [row for row in rows if row["dataset_split"] == split]
        split_details[split] = {"rows": len(subset), "scenario_times": len({r["target_time_dhaka"] for r in subset}),
                                "from": min(r["target_time_dhaka"] for r in subset), "to": max(r["target_time_dhaka"] for r in subset)}
    metadata = {
        "model_version": f"road-risk-bilingual-v2-{fingerprint[:12]}", "data_source": "synthetic",
        "dataset": "packages/new-data", "dataset_hashes": hashes, "mapping_sha256": mapping_hash,
        "training_code_sha256": recipe_hash,
        "rows": len(rows), "segments": len(profiles), "map_roads": len(mapping["roads"]),
        "mapped_segments": len({s for ids in mapping["roads"].values() for s in ids}),
        "split_counts": dict(Counter(row["dataset_split"] for row in rows)), "splits": split_details,
        "serving_training_rows": int(serving_mask.sum()), "test_rows": int(masks["test"].sum()),
        "features": DATASET_FEATURES, "classification_thresholds": best["thresholds"],
        "threshold_selection": "Maximize each label's F1 on 2025 validation only, grid 0.05..0.95; highest threshold wins ties. Probability color bands are separate from these screening thresholds.",
        "excluded_features": ["all future target_* outcomes and reasons", "year", "segment IDs and bilingual name duplicates",
                              "rainfall_last_*", "recent_speed_kmh_sim", "traffic_demand_index_sim_0to100",
                              "nearby_event_sim_0or1", "congestion_level_en", "rain_condition_en"],
        "feature_policy": "Only target time, forecast horizon, scenario rain and static road profiles are available in the app. No unavailable telemetry is invented or imputed.",
        "model_selection": "Mean validation average precision across both labels; test data never used for tuning.",
        "candidates": candidates, "selected_parameters": best["parameters"],
        "evaluation": metrics(test_y, test_probabilities, best["thresholds"]),
        "evaluation_at_0_5": metrics(test_y, test_probabilities), "evaluation_by_corridor": by_corridor,
        "evaluation_by_month": by_month,
        "constant_prevalence_baseline": metrics(test_y, np.tile(y[serving_mask].mean(axis=0), (len(test_y), 1))),
        "split": "2024 train, 2025 validation for selection; refit 2024+2025; evaluate on untouched Jan-Sep 2026.",
        "aggregation": mapping["aggregation"], "mapping_basis": mapping["basis"],
        "scikit_learn_version": sklearn.__version__,
        "trained_at": datetime.now(DHAKA).isoformat(),
        "limitations": "Synthetic simulator data with only 99 shared scenarios. Sparse hour and rain coverage. No real-world accuracy established. Uncalibrated probabilities; a corridor displays its highest segment probability, not a probability of the entire corridor being closed.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    joblib.dump({"format": 2, "features": DATASET_FEATURES, "model": model, "metadata": metadata,
                 "profiles": profiles, "road_segments": mapping["roads"]}, temporary)
    temporary.replace(output)
    output.with_suffix(".report.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), "utf-8")
    return metadata
