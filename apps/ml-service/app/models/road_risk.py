"""Independent, versioned road-risk model. All initial labels are simulated."""
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import numpy as np

from app.models.road_features import DATASET_FEATURES, binary_probabilities, dataset_features

REPO_ROOT = Path(__file__).resolve().parents[4]
CATALOG = json.loads((REPO_ROOT / "packages/data/dhaka-main-roads.json").read_text("utf-8"))
DHAKA = timezone(timedelta(hours=6), name="Asia/Dhaka")
FEATURES = ["hour_sin", "hour_cos", "weekday", "month", "rainfall_mm",
            "flood_factor", "traffic_factor"]


def features(at: datetime, rainfall_mm: float, road: dict) -> list[float]:
    local = at.astimezone(DHAKA)
    hour = local.hour + local.minute / 60
    return [math.sin(hour * math.pi / 12), math.cos(hour * math.pi / 12),
            local.weekday(), local.month, rainfall_mm,
            road["flood_factor"], road["traffic_factor"]]


class RoadRiskModel:
    def __init__(self, artifact):
        self.format = artifact.get("format")
        expected = DATASET_FEATURES if self.format == 2 else FEATURES
        if artifact.get("features") != expected or self.format not in (1, 2):
            raise ValueError("Incompatible road-risk artifact; retrain")
        self.model = artifact["model"]
        self.metadata = artifact["metadata"]
        self.profiles = artifact.get("profiles", {})
        self.road_segments = artifact.get("road_segments", {})
        if self.format == 2:
            if set(self.road_segments) != {road["id"] for road in CATALOG}:
                raise ValueError("Artifact mapping does not match the current map catalog")
            if any(not ids or not set(ids) <= set(self.profiles) for ids in self.road_segments.values()):
                raise ValueError("Artifact contains unknown or empty segment mappings")

    @classmethod
    def load(cls, path: Path):
        return cls(joblib.load(path))

    def predict(self, at: datetime, rainfall_mm: float, forecast_horizon_min: int = 60):
        if self.format == 2:
            return self.predict_dataset(at, rainfall_mm, forecast_horizon_min)
        matrix = np.asarray([features(at, rainfall_mm, road) for road in CATALOG])
        probabilities = self.model.predict_proba(matrix)
        risks = []
        for index, road in enumerate(CATALOG):
            values = []
            for output, classes in zip(probabilities, self.model.classes_, strict=True):
                values.append(float(output[index, list(classes).index(1)]) if 1 in classes else 0.0)
            flood, traffic = values
            # Overall risk is the greater of the two; do not assume independence.
            risk = max(values)
            risks.append({"road_id": road["id"], "waterlogging_probability": round(flood, 4),
                          "traffic_probability": round(traffic, 4),
                          "risk": "high" if risk >= .65 else "moderate" if risk >= .35 else "low"})
        return {"at": at.astimezone(DHAKA).isoformat(), "timezone": "Asia/Dhaka",
                "rainfall_mm": rainfall_mm, "weather_source": "user_scenario",
                "data_source": self.metadata["data_source"],
                "model_version": self.metadata["model_version"],
                "notice": "Synthetic-data scenario. Not a verified forecast or live traffic feed.",
                "roads": risks}

    def predict_dataset(self, at: datetime, rainfall_mm: float, forecast_horizon_min: int):
        segment_ids = list(self.profiles)
        matrix = np.asarray([dataset_features(at, rainfall_mm, self.profiles[segment_id], forecast_horizon_min)
                             for segment_id in segment_ids])
        probabilities = binary_probabilities(self.model, matrix)
        index = {segment_id: i for i, segment_id in enumerate(segment_ids)}
        roads = []
        for road_id, mapped in self.road_segments.items():
            water, traffic = probabilities[[index[segment_id] for segment_id in mapped]].max(axis=0)
            risk = max(water, traffic)
            roads.append({"road_id": road_id, "waterlogging_probability": round(float(water), 4),
                          "traffic_probability": round(float(traffic), 4),
                          "risk": "high" if risk >= .65 else "moderate" if risk >= .35 else "low",
                          "waterlogging_alert": bool(water >= self.metadata["classification_thresholds"]["waterlogging"]),
                          "traffic_alert": bool(traffic >= self.metadata["classification_thresholds"]["traffic_jam"]),
                          "segment_ids": mapped, "aggregation": "maximum_segment_probability"})
        return {"at": at.astimezone(DHAKA).isoformat(), "timezone": "Asia/Dhaka",
                "issue_time": (at - timedelta(minutes=forecast_horizon_min)).astimezone(DHAKA).isoformat(),
                "forecast_horizon_min": forecast_horizon_min,
                "rainfall_mm": rainfall_mm, "weather_source": "user_scenario",
                "data_source": self.metadata["data_source"], "model_version": self.metadata["model_version"],
                "aggregation": "maximum_segment_probability",
                "classification_thresholds": self.metadata["classification_thresholds"],
                "coverage": {"trained_segments": len(segment_ids), "map_roads": len(roads),
                             "mapped_segments": self.metadata["mapped_segments"]},
                "notice": "Synthetic-data scenario. Corridor values show the highest mapped segment probability, not verified closures or live traffic.",
                "roads": roads}
