# Training the map model with packages/new-data

The map model now uses the supplied bilingual dataset in `packages/new-data` by default.
These files explicitly declare their observations and road topology **synthetic**.
The Excel preview duplicates a subset of the CSV; it is not added as extra training data.

## Reproduce

From `apps/ml-service`, run:

```powershell
uv run python -m app.train_road_risk --dataset ../../packages/new-data
```

This validates the CSVs, selects a model and decision thresholds using validation data,
evaluates the final model on the separate test period, and saves `weights/road-risk.joblib`
with `weights/road-risk.report.json`. Invalid data fails before replacing a working artifact.
Restart the ML service after an intentional retrain.

To train a candidate without replacing the active local weights:

```powershell
uv run python -m app.train_road_risk --dataset ../../packages/new-data --output weights/road-risk-new-data.candidate.joblib
```

The local Docker image includes the new CSVs and mapping. From the repository root, retrain
its persistent model volume and restart only ML:

```powershell
docker compose --project-directory infra -f infra/docker-compose.local.yml exec ml-service uv run --no-sync python -m app.train_road_risk --dataset /workspace/packages/new-data
docker compose --project-directory infra -f infra/docker-compose.local.yml restart ml-service
```

Rebuild the ML image after changing the input CSVs or mapping, since those are copied into
the image. Application code is mounted during local development. Existing weights are
preserved on ordinary startup; a populated model volume is not retrained silently.
The complaint classifier is a separate artifact and is not replaced by these commands.

The old generator remains available explicitly:

```powershell
uv run python -m app.train_road_risk --generate --days 365 --output weights/legacy-road-risk.joblib
```

## What was used

| Partition | Period | Rows | Shared target times |
| --- | --- | ---: | ---: |
| Training | 2024 | 7,560 | 36 |
| Validation | 2025 | 7,560 | 36 |
| Test | January–September 2026 | 5,670 | 27 |
| Total | 2024–2026 | 20,790 | 99 |

The directed-segment CSV contains 210 edges and the junction CSV contains 77 junctions.
The importer validates keys, joins, numeric ranges, binary labels, the OR label, Dhaka time
offsets, 30/60/120 minute horizons, stable road attributes, and non-overlapping temporal
partitions. Shared target timestamps remain in one partition. Static serving profiles
come from training rows, not from future test outcomes.

Two random forest configurations are compared by mean validation **average precision**
across rainwater and traffic targets. Each target's screening threshold is selected by
validation F1 on a fixed 0.05–0.95 grid; higher thresholds win ties. The chosen configuration
is refitted on the 15,120 training-plus-validation rows and evaluated on 5,670 untouched
test rows. Test examples are not added to the final fit. The saved report includes
precision, recall, F1, average precision, Brier score, confusion counts, prevalence,
per-corridor/month results, constant-prevalence baselines, input/mapping/code hashes,
and the installed scikit-learn version. Default-threshold (0.5) results are also retained.

The UI's 35%/65% probability color bands are separate from the validation-selected
binary screening thresholds. Those thresholds and screening flags are exposed by ML;
they do not turn the map's percentages into verified closures.

## Training and serving use the same inputs

The map can supply a target time, scenario rainfall, and forecast horizon. The artifact
also stores each dataset segment's assumed length, lanes, baseline congestion, flood
susceptibility, and drainage capacity. Training and serving share the exact transformation
for cyclic hour, weekday, month, Bangladesh weekend/rush-hour indicators, horizon,
scenario rainfall, and those five static attributes: 13 numeric features total.

Future blockage labels, future reasons and future travel time are excluded from inputs.
The dataset's recent speed, earlier rainfall, traffic demand, and nearby-event fields
are valid issue-time data, but the app has no feeds or controls for them. They are
deliberately excluded rather than silently replaced by fabricated live readings.
This restricts prediction quality; adding verified telemetry later should include both
training features and matching inference inputs. English/Bangla duplicate names and
segment IDs are not used as numeric shortcuts.

## Mapping the dataset back to the map

`packages/data/dhaka-road-segment-mapping.json` explicitly connects the existing 14 map
corridors to 82 covered directed segments. The model is trained across all 210 segments;
the remaining 128 currently have no map overlay. The supplied junction file has no
coordinates, so no new geographic positions are invented.

Inference evaluates the mapped dataset segment profiles and shows the **highest segment
probability** for each hazard in each displayed corridor. This is a score for the most
at-risk mapped segment, not a calibrated probability that the entire corridor is closed
or a probability union across directions. The conceptual dataset-to-corridor mappings
still require geospatial validation because the supplied junctions have no coordinates.
The display shapes now use checked-in OpenStreetMap geometry (see [map geometry](LIVE_MAP.md#road-catalog-and-geometry));
updating those shapes does not make the synthetic dataset geographically observed.

`GET /api/v1/map/predictions` accepts `forecast_horizon_min=30|60|120`, default 60, and
forwards it to ML. The map offers the same choices and hides stale results when the time,
rainfall, or horizon changes. `GET http://localhost:8001/road-risk/model` identifies the
active model and its full report.

## Interpretation

Only 99 independent shared time scenarios are present, despite the 20,790 road rows.
Water blockage is rare, and scenario hours/rain amounts are sparse. Metrics measure
learning this simulator with the available map inputs, not real-world Dhaka forecast
accuracy. The probabilities are uncalibrated and no live weather/traffic is fetched.
Keep these limitations in the project presentation.

Metric definitions follow the [scikit-learn evaluation documentation](https://scikit-learn.org/stable/modules/model_evaluation.html).
