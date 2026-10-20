"""Features available to the map: known target time, scenario rain and static road data.

Deliberately excludes recent speed, events, demand and prior rainfall: the app has
no live feeds for them. Training and inference share this exact transformation.
"""
import math
from datetime import datetime, timedelta, timezone

import numpy as np

DHAKA = timezone(timedelta(hours=6), name="Asia/Dhaka")
STATIC_COLUMNS = {
    "estimated_length_km": (.01, 100),
    "assumed_lane_count": (1, 20),
    "baseline_congestion_sim_0to1": (0, 1),
    "flood_susceptibility_sim_0to1": (0, 1),
    "drainage_capacity_sim_0to100": (0, 100),
}
DATASET_FEATURES = [
    "hour_sin", "hour_cos", "weekday", "month", "is_weekend_fri_sat",
    "is_peak_hour", "forecast_horizon_min", "forecast_rain_target_1h_mm_sim",
    *STATIC_COLUMNS,
]
TARGETS = ["waterlogging", "traffic_jam"]


def dataset_features(at: datetime, rain: float, profile: dict, horizon: int = 60):
    if at.tzinfo is None:
        raise ValueError("Prediction time must include a timezone")
    local = at.astimezone(DHAKA)
    hour = local.hour + local.minute / 60
    return [math.sin(hour * math.pi / 12), math.cos(hour * math.pi / 12),
            local.weekday(), local.month, int(local.weekday() in (4, 5)),
            int(7 <= local.hour <= 10 or 16 <= local.hour <= 20), horizon, rain,
            *(profile[column] for column in STATIC_COLUMNS)]


def binary_probabilities(model, matrix):
    outputs = model.predict_proba(matrix)
    return np.column_stack([
        output[:, list(classes).index(1)] if 1 in classes else np.zeros(len(matrix))
        for output, classes in zip(outputs, model.classes_, strict=True)
    ])
