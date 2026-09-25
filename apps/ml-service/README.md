# DubsiBhai ML Service

FastAPI service for Bengali complaint classification. The initial model uses the synthetic
CSV in `docs/dataset/drainage_complaints_bn.csv` and predicts six categories:
`blocked_drain`, `open_manhole`, `road_flooding`, `waterlogging_recurring`, `sewage_overflow`, and `other`.

## Train and run

From this directory (`apps/ml-service`):

```powershell
./train.ps1
./run.ps1
```

Training installs locked dependencies, validates the CSV, evaluates a TF-IDF character n-gram
and logistic regression pipeline, then refits it on all unique texts for serving. No GPU is needed.
The serving artifact is `weights/classifier.joblib`; `weights/classifier.report.json` records
the dataset hash, model version, class counts, evaluation results, and limitations.
Both are local, gitignored outputs. Teammates must train after cloning.

`run.ps1` loads the saved model at startup; it does not retrain automatically.
Restart the ML service after training or replacing its model. Press Ctrl+C to stop.

Equivalent training command after `uv sync --locked`:

```powershell
uv run python -m app.train
```

## API

### Interactive notebook

Open [classifier_experiments.ipynb](notebooks/classifier_experiments.ipynb) to test the
saved model, compare Bengali examples, view class probabilities, and inspect the holdout report.
From `apps/ml-service`, install the optional notebook dependencies:

```powershell
uv sync --locked --group notebooks
```

In VS Code, select this service's `.venv/Scripts/python.exe` as the notebook kernel,
then choose **Run All**. Local predictions do not require the API server. The live API
test is optional and disabled by default. After running the service launcher, rerun the
notebook dependency command if uv removed the optional group.

Swagger UI: http://localhost:8001/docs.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Process liveness, independent of the model |
| `GET /ready` | Returns 200 only when a classifier is loaded; otherwise 503 |
| `POST /classify` | Classify a complaint supplied as `{"text": "..."}` |
| `GET /model` | Inspect model metadata and its training report |

Example request body for `/classify` in Swagger UI:

```json
{"text": "ম্যানহোলের ঢাকনা নেই, বাচ্চারা পড়ে যেতে পারে।"}
```

The response includes `predicted_category`, `confidence`, a `probabilities` map for all six
categories, `model_version`, and `data_source`. Confidence is an uncalibrated model probability,
not a guarantee of correctness. The classifier always selects one of the six categories;
unrelated or unfamiliar text may still receive an incorrect prediction.
Blank text, missing text, and text longer than 5000 characters return 422.
If the artifact is missing, corrupt, or incompatible, classification returns 503 with a
training instruction while `/health` remains available. Startup logs contain the load error.

## Replace the dataset and retrain

Keep these UTF-8 CSV columns: `id`, `text_bn`, `category`.
IDs must be unique and nonempty. Use the same six category names and provide at least two
distinct texts per category; a useful real evaluation will need substantially more data.
Exact duplicate texts are normalized and deduplicated before the split. Conflicting labels,
unknown categories, blank texts, and duplicate IDs fail validation without replacing a working model.

After replacing the default CSV with real examples:

```powershell
./train.ps1 -DataSource real
```

Or point to a separate file, with paths resolved from your current directory:

```powershell
./train.ps1 -Dataset ../../docs/dataset/real_complaints_bn.csv -DataSource real
```

Use `-DataSource mixed` if combining synthetic and real examples. The source flag records
your declaration; it does not detect the origin of individual rows.
Review `weights/classifier.report.json`, then restart the ML service.
Changing the category taxonomy requires updating the code and its API consumers too.

## Evaluation limits

The default evaluation is a reproducible 80/20 stratified holdout after normalized exact-text
deduplication (seed 42). Feature extraction is fitted only on the training split for evaluation.
The final serving model is then refitted on all unique texts; the holdout metrics describe the
evaluation model, not an independent evaluation of that final refit.

Initial synthetic run: **360 rows, 295 unique texts, 65 duplicates removed; 236 training and
59 holdout examples; 98.3% holdout accuracy and 0.983 macro F1**.
Template variants can appear in both splits, so these scores do not measure performance on
real residents' complaints. Keep independent real examples for a later evaluation.

The training pipeline follows scikit-learn's
[TF-IDF](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
and [logistic regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html)
interfaces.

## Configuration and checks

Configuration is in `app/core/config.py` and reads the root `.env` using the `ML_` prefix.
Optional `ML_MODEL_PATH` overrides the artifact path; prefer an absolute path. Training uses
the same setting unless its Python CLI receives `--output`. Load only trusted, locally trained
joblib artifacts, since deserialization can execute code. Retrain after changing scikit-learn versions.

```powershell
uv run pytest
uv run ruff check app tests
```

Duplicate detection, geographic clustering, queue processing, and core API integration remain
separate planned features. The CSV provides category labels for classification only.
The exploratory script in `docs/dataset/train.py` produces a different artifact format;
use this service's `train.ps1` to create the artifact served by this API.
