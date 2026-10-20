# Dhaka live map and road-risk demo

The active training path now uses the bilingual CSVs in `packages/new-data`: 20,790
simulated observations over 210 directed segments. See [training with the supplied
dataset](ROAD_DATASET_TRAINING.md) for the current features, fixed time partitions,
forecast horizons, mapping and deployment commands. The generator described below
is the optional legacy baseline; select it explicitly with `--generate`.

Open `/map`. The page has three views:

1. **Community reports**: public complaints and recent road observations; refreshed every 20 seconds.
2. **Road updates**: tap a highlighted corridor or choose a road in the searchable list. The selected segment shows its endpoints and a quick reporting form. Signed-in contributors can report a blocked/difficult or clear/passable road, or file a complaint. Submissions use the existing authenticated, CSRF-protected complaints workflow and persist the selected `road_id`.
3. **Predicted risk**: choose a date/time in **Asia/Dhaka (UTC+6)** and scenario rainfall in **mm in one hour**, then run inference. Switch between rainwater obstruction and traffic congestion. Dashed lines separate model output visually from observations. Gray means no prediction; green <35%, amber 35–64%, red ≥65%. Changing inputs hides the old result until inference runs again.

Only curated Dhaka main roads are selectable. Residential lanes and block roads are excluded from the road catalog for this map. The ordinary base map can still show local streets as geographic context. Existing reports elsewhere in Dhaka remain available in the community view.

## Map provider

The default uses **Leaflet 1.9.4** and **OpenStreetMap** raster tiles, without a Google API key. Tiles keep OSM attribution, browser caching, and an origin Referer; there is no bulk downloading or offline prefetch. For a larger deployment, choose a tile provider or self-host tiles according to the [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/).

To switch the live map to Google Maps later, put these in `apps/web/.env.local`:

```dotenv
NEXT_PUBLIC_MAP_PROVIDER=google
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_browser_restricted_key
```

Enable the Maps JavaScript API for that key, allow the site's origins, and restart Next.js (rebuild production images). The browser key is public by design and should have website/API restrictions. `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is a separate Google sign-in setting. Without an explicit provider, a configured Maps key selects Google automatically; `NEXT_PUBLIC_MAP_PROVIDER=osm` explicitly keeps OSM.

Both renderers consume the same road/report/prediction data and selection callback. Switching provider requires no backend or model changes. Google API loading follows its [JavaScript API loader documentation](https://developers.google.com/maps/documentation/javascript/load-maps-js-api). The default renderer uses [Leaflet's public API](https://leafletjs.com/reference.html).

## Road catalog and geometry

`packages/data/dhaka-main-roads.json` is shared by the API and ML service. It defines **14 corridors** with stable IDs, names, endpoints, assumed flood/traffic factors, and detailed **OpenStreetMap road geometry** downloaded on 20 October 2026. The old sparse hand-entered paths were replaced because their straight lines cut across the actual roads. The factors remain simulator assumptions, not measured assessments of real roads.

`paths` contains separate latitude/longitude arrays for the source OSM ways, including separate carriageways. Both map renderers preserve these sections without connecting unrelated endpoints. The legacy `path` field contains only the longest section; new clients should use `paths`. Catalog centers lie on a source way. Each entry records its OSM way IDs, geometry source and retrieval time. Reports and model predictions still apply to the selected corridor as a whole; these shapes do not provide turn-by-turn navigation.

The attributed source snapshot is `packages/data/dhaka-osm-road-source.json`. It contains only the selected main-road ways and is distributed under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). Source names and corridor clipping bounds are in `dhaka-road-geometry-selection.json`. Reproduce the checked-in catalog offline from the repository root:

```bash
python scripts/import-road-geometry.py --overpass-json packages/data/dhaka-osm-road-source.json
```

For future updates, retrieve the named main roads using [Overpass `out geom`](https://dev.overpass-api.de/overpass-doc/en/targets/turbo.html), or download bounded OSM XML extracts and use `--osm-dir <directory> --retrieved-at <ISO timestamp>`. Review names, corridor bounds and source attribution before importing; the script deliberately refuses to write when a corridor has no matching geometry. The page uses the checked-in geometry and makes no live Overpass calls. Only source ways marked trunk, primary, secondary or tertiary can be selected by the importer; residential lanes are excluded.

Migration `20261020_04` adds these roads and their areas; bootstrap also seeds missing rows idempotently. Existing catalogs and reports are preserved. `GET /api/v1/map/roads?main_only=true` returns just these IDs, including paths and endpoint names. The existing unfiltered endpoint remains available for other workflows. To add corridors, edit the catalog, run bootstrap, retrain, and rebuild the service images.

Changing shapes for existing IDs does not require ML retraining: geometry is not a prediction feature. Bootstrap also repairs the saved center coordinates for these catalog roads. Docker images bake in `packages/data`, so rebuild the API image (or run the usual `./start.ps1` / `bash scripts/start.sh`) after importing new shapes. A host API reload picks up catalog changes after restart. OSM and Google may update their map imagery on different schedules, so small provider differences remain possible.

## Model architecture

Keep road-risk prediction **inside the existing ML microservice**, with its own module, model artifact, training command, metadata, and endpoints. Complaint classification and priority workflows continue independently. The core API owns user data and reporting; the browser calls the core API, which calls ML over the internal network.

This avoids another deployment, environment, and monitoring stack for a small CPU model. Extract a separate road-risk service when inference traffic, scaling, model dependencies, or the team lifecycle requires independent deployment. The `/road-risk` HTTP interface makes that extraction straightforward.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/map/predictions?at=<ISO timestamp with offset>&rainfall_mm=25` | Public core API proxy; validates rainfall and a time within seven days of now |
| `POST /road-risk/predict` on ML | Internal inference, body `{"at":"2026-10-20T18:00:00+06:00","rainfall_mm":25}` |
| `GET /road-risk/model` on ML | Version, dataset hash, evaluation and limitations |

Missing or incompatible road-risk weights produce 503 for prediction while complaint classification and liveness remain independent. `/ready` continues to mean the complaint classifier is ready; it does not promise that the road model is loaded.

## Generate and train

The Windows ML launcher and complete local Docker stack train missing road-risk weights automatically. To generate/retrain explicitly:

```powershell
cd apps/ml-service
uv run python -m app.train_road_risk
```

Restart ML after training. API catalog migration can be applied separately:

```powershell
cd apps/api
uv run alembic upgrade head
```

Optional legacy generation (`--generate`) creates **122,640 rows**: 14 segments × 365 days × 24 hours, with seed 42. Outputs are local and gitignored:

- `apps/ml-service/weights/road_risk_synthetic.csv`
- `apps/ml-service/weights/road-risk.joblib`
- `apps/ml-service/weights/road-risk.report.json`

Optional root setting `ML_ROAD_RISK_MODEL_PATH` changes the artifact location. A smaller reproducible experiment can use `--days 30`; the default is a full simulated year.

The dataset contains `road_id`, offset-aware `at`, `rainfall_mm`, and binary `waterlogging`/`traffic_jam` labels. Generation simulates seasonal rain, rush hours, the Bangladesh Friday/Saturday weekend, road factors, and random outcomes. No user reports, weather observations, or measured traffic are included. The two labels represent simulated travel obstruction, not a legal road closure.

A multi-output random forest predicts the two probabilities from cyclic hour features, weekday, month, rainfall, and assumed road factors. Evaluation uses the earlier 80% of timestamps for training and the later 20% for holdout, grouping every road at the same timestamp together. F1 and Brier scores are recorded separately for each label; the serving model is then fitted on all rows. The generated labels are stochastic, so perfect scores are neither expected nor desirable.

**Presentation wording:** “Our working prototype combines community observations and an independent road-risk model using open-source maps. The initial model is trained on generated hourly scenarios. It demonstrates the prediction pipeline; real-world forecast accuracy has not yet been established. We can switch the live map to Google Maps through environment settings.”

The displayed probabilities are uncalibrated model outputs. Synthetic holdout scores measure how well the model learns the simulator, not performance on Dhaka roads. Before treating this as a real forecast, collect independently observed road conditions and timestamped weather/traffic features, replace the simulated factors and labels, retrain, calibrate, and validate on a separate real time period. Do not relabel generated rows as real observations.
