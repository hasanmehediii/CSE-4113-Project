# Bengali complaint classifier: synthetic baseline

Model: `20261030T094240392338Z-b958a49536db`. Trained: 2026-10-30T09:42:40.392338+00:00.

Complaint category classifier trained on the bundled synthetic Bengali dataset at
`docs/dataset/drainage_complaints_bn.csv`. This is the initial baseline model used
for the classification pipeline. Template-generated text; no real resident complaints
are included. Metrics reflect how well the model learns the synthetic templates, not
real-world complaint diversity.

Algorithm: character TF-IDF (2–5-gram n-grams), sublinear TF, balanced logistic
regression (max_iter=1000, seed=42). No GPU required.

## Dataset

360 input rows → 295 unique texts after NFC normalization and exact-text deduplication
(65 duplicates removed). Class distribution after deduplication:

| Category | Unique texts |
| --- | ---: |
| `blocked_drain` | 47 |
| `open_manhole` | 44 |
| `road_flooding` | 53 |
| `waterlogging_recurring` | 48 |
| `sewage_overflow` | 53 |
| `other` | 50 |

## Holdout evaluation

Stratified 80/20 split after deduplication, seed 42. Features fitted on training
split only. Serving model then refitted on all 295 unique texts.

| Split | Rows |
| --- | ---: |
| Training | 236 |
| Holdout | 59 |
| Serving refit | 295 |

| Metric | Value |
| --- | ---: |
| Accuracy | 0.9831 |
| Macro F1 | 0.9833 |

Per-class results on the 59 holdout examples:

| Category | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `blocked_drain` | 1.000 | 1.000 | 1.000 | 9 |
| `open_manhole` | 1.000 | 1.000 | 1.000 | 9 |
| `road_flooding` | 1.000 | 0.900 | 0.947 | 10 |
| `waterlogging_recurring` | 0.909 | 1.000 | 0.952 | 10 |
| `sewage_overflow` | 1.000 | 1.000 | 1.000 | 11 |
| `other` | 1.000 | 1.000 | 1.000 | 10 |

One `road_flooding` example was misclassified as `waterlogging_recurring`. These
categories share vocabulary in the synthetic templates; the confusion is expected and
documented. All other categories are perfectly separated.

## Limitations

- Template-generated text: the model learns template phrasing, not the full range
  of real resident vocabulary, typos, code-mixing or dialectal variation.
- Confidence values are not calibrated.
- Holdout scores do not establish real-world accuracy.
- Synthetic template variants may appear in both splits, inflating scores.
- Evaluate on independently collected real complaints before drawing deployment
  conclusions or reporting accuracy to stakeholders.

## Reproducibility

Dataset SHA-256: `b958a49536db6320cd2104a3ef5eeb54ecff847e4eb85bd0f38307d890269772`.

scikit-learn version: `1.9.1`.

See [the ML service README](../../apps/ml-service/README.md) for training commands
and [the dataset README](../dataset/DATASET_README.md) for dataset provenance.
To retrain: `./apps/ml-service/train.ps1` (uses bundled CSV by default).
To retrain with real data: `./apps/ml-service/train.ps1 -Dataset path/to/real.csv -DataSource real`.
