"""Generate the synthetic historical traffic/waterlogging profile for the map's main roads.

No real observations exist for these roads, so this simulates two years of hourly
conditions (2024-01-01 to 2025-12-31) from documented assumptions and the catalog's
per-road `flood_factor` and `traffic_factor`, then stores how often each road was jammed
or waterlogged for every season x day type x hour, overall ("any") and by the city's rain
in the previous 3 hours ("none", "light", "heavy"). The rain-conditioned values let the
API combine current weather with history. Synthetic demonstration data, not a record of
Dhaka; replace it with real observations later. Deterministic: same seed, same file.

    python scripts/generate-road-history.py            # writes packages/data/dhaka-road-history.json
    python scripts/generate-road-history.py --check    # fails if the checked-in file is out of date
"""
import argparse
import json
import math
import random
import sys
from collections import deque
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "packages/data/dhaka-main-roads.json"
OUTPUT = ROOT / "packages/data/dhaka-road-history.json"
SEED = 2026
START, END = date(2024, 1, 1), date(2025, 12, 31)

# Bangladesh seasons as used by the map; months are 1-12.
SEASONS = {"dry": [12, 1, 2], "pre_monsoon": [3, 4, 5], "monsoon": [6, 7, 8, 9], "post_monsoon": [10, 11]}
# Dhaka's weekend is Friday and Saturday. Python weekday(): Monday=0 ... Sunday=6.
DAY_TYPES = {"workday": [6, 0, 1, 2, 3], "friday": [4], "saturday": [5]}
# Share of days with rain and mean rain-hour intensity (mm/h), a rough monsoon calendar.
RAIN_DAY = {1: .04, 2: .08, 3: .14, 4: .28, 5: .45, 6: .70, 7: .80, 8: .76, 9: .64, 10: .32, 11: .08, 12: .04}
RAIN_MM = {1: 2.0, 2: 2.5, 3: 4.0, 4: 6.0, 5: 8.0, 6: 9.0, 7: 9.5, 8: 9.0, 9: 8.5, 10: 6.5, 11: 3.0, 12: 2.0}
# City rainfall in the previous 3 hours (mm); the API uses the same bands for Open-Meteo data.
RAIN_BANDS = {"none": 0.5, "light": 8.0}  # none < 0.5 <= light < 8 <= heavy
# Fewer simulated hours than this in a rain-band bucket pools it across seasons, then day types.
MIN_HOURS = 8


def rain_band(rain_3h: float) -> str:
    return "none" if rain_3h < RAIN_BANDS["none"] else "light" if rain_3h < RAIN_BANDS["light"] else "heavy"


def season_of(month: int) -> str:
    return next(name for name, months in SEASONS.items() if month in months)


def day_type_of(weekday: int) -> str:
    return next(name for name, days in DAY_TYPES.items() if weekday in days)


def base_traffic(hour: int, day_type: str) -> float:
    """Typical chance of a jam by hour before road and weather effects."""
    if day_type == "friday":
        # Quiet morning, Jumu'ah midday, busy evening outings.
        curve = {**dict.fromkeys(range(0, 7), .03), **dict.fromkeys(range(7, 12), .12),
                 **dict.fromkeys(range(12, 15), .30), **dict.fromkeys(range(15, 18), .35),
                 **dict.fromkeys(range(18, 22), .55), **dict.fromkeys(range(22, 24), .15)}
    else:
        curve = {**dict.fromkeys(range(0, 6), .03), 6: .15, 7: .45, 8: .78, 9: .82, 10: .62,
                 **dict.fromkeys(range(11, 16), .42), 16: .58, 17: .82, 18: .88, 19: .80, 20: .58,
                 21: .35, 22: .15, 23: .08}
        if day_type == "saturday":
            curve = {hour_: value * .75 for hour_, value in curve.items()}
    return curve[hour]


def rain_hours(rng: random.Random, day: date) -> list[float]:
    """Hourly city-wide rainfall for one day (mm in each hour)."""
    rain = [0.0] * 24
    if rng.random() >= RAIN_DAY[day.month]:
        return rain
    for _ in range(rng.choice((1, 1, 2, 2, 3))):
        # Showers favour the afternoon and evening during the monsoon.
        start = min(23, max(0, int(rng.gauss(15 if day.month in SEASONS["monsoon"] else 13, 5))))
        for hour in range(start, min(24, start + rng.choice((1, 2, 2, 3, 4)))):
            rain[hour] += rng.expovariate(1 / RAIN_MM[day.month])
    return rain


def simulate(roads: list[dict]):
    rng = random.Random(SEED)
    counts = {road["id"]: {hazard: {} for hazard in ("traffic", "waterlogging")} for road in roads}
    samples: dict[tuple, int] = {}
    water = {road["id"]: 0.0 for road in roads}
    recent = deque([0.0, 0.0, 0.0], maxlen=3)
    day = START
    while day <= END:
        rain = rain_hours(rng, day)
        for hour in range(24):
            recent.append(rain[hour])
            base = (season_of(day.month), day_type_of(day.weekday()), hour)
            band = rain_band(sum(recent))
            for key in (base + ("any",), base + (band,)):
                samples[key] = samples.get(key, 0) + 1
            for road in roads:
                flood, busy = road["flood_factor"], road["traffic_factor"]
                # Standing water builds with rain, more on flood-prone roads, and drains each hour.
                water[road["id"]] = water[road["id"]] * (0.35 + 0.4 * flood) + rain[hour] * (0.4 + flood)
                waterlogged = water[road["id"]] > 9 + rng.gauss(0, 1.5)
                chance = base_traffic(hour, key[1]) * (0.55 + 0.5 * busy)
                chance += (0.18 if rain[hour] > 2 else 0) + (0.22 if waterlogged else 0)
                jammed = rng.random() < min(0.97, chance)
                for hazard, happened in (("traffic", jammed), ("waterlogging", waterlogged)):
                    bucket = counts[road["id"]][hazard]
                    for key in (base + ("any",), base + (band,)):
                        bucket[key] = bucket.get(key, 0) + int(happened)
        day += timedelta(days=1)
    return counts, samples


def rate(counts: dict, samples: dict, season: str, day_type: str, hour: int, band: str) -> float:
    """Share of hours with the hazard; sparse rain-band buckets pool across seasons, then day types."""
    for seasons, day_types in (([season], [day_type]), (list(SEASONS), [day_type]),
                               (list(SEASONS), list(DAY_TYPES))):
        keys = [(s, d, hour, band) for s in seasons for d in day_types]
        hours = sum(samples.get(key, 0) for key in keys)
        if band == "any" or hours >= MIN_HOURS:
            return round(sum(counts.get(key, 0) for key in keys) / hours, 2) if hours else 0.0
    return rate(counts, samples, season, day_type, hour, "any")


def build() -> dict:
    roads = json.loads(CATALOG.read_text("utf-8"))
    counts, samples = simulate(roads)
    bands = ("any", "none", "light", "heavy")
    profile = {}
    for road in roads:
        profile[road["id"]] = {
            hazard: {season: {day_type: {band: [rate(counts[road["id"]][hazard], samples, season, day_type, hour, band)
                                               for hour in range(24)] for band in bands}
                              for day_type in DAY_TYPES} for season in SEASONS}
            for hazard in ("traffic", "waterlogging")
        }
    return {
        "data_source": "synthetic",
        "notice": "Simulated history for demonstration. Not observed Dhaka traffic or flooding.",
        "generated_by": "scripts/generate-road-history.py",
        "seed": SEED,
        "simulated_period": f"{START.isoformat()} to {END.isoformat()}, hourly",
        "value": "share of simulated hours with a traffic jam or waterlogging",
        "layout": "roads[road][hazard][season][day_type][rain_band][hour]",
        "rain_bands": {"any": "all hours", "none": "< 0.5 mm in the previous 3 h",
                       "light": "0.5-8 mm in the previous 3 h", "heavy": ">= 8 mm in the previous 3 h"},
        "pooling": f"rain-band buckets with fewer than {MIN_HOURS} simulated hours pool across seasons, then day types",
        "timezone": "Asia/Dhaka",
        "seasons": SEASONS,
        "day_types": {"workday": "Sunday-Thursday", "friday": "Friday", "saturday": "Saturday"},
        "hours_per_bucket": {f"{s}/{d}": min(samples[(s, d, h, "any")] for h in range(24))
                             for s in SEASONS for d in DAY_TYPES},
        "roads": profile,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify the checked-in file is up to date")
    args = parser.parse_args(argv)
    text = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.check:
        if OUTPUT.read_text("utf-8") != text:
            print(f"{OUTPUT.relative_to(ROOT)} is out of date; rerun scripts/generate-road-history.py")
            return 1
        print("road history is up to date")
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(text) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
